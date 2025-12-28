import discord
from discord.ext import commands
import anthropic
from openai import OpenAI
from google import genai
import os
import json
import sys
from typing import Optional
import asyncio
from dotenv import load_dotenv
import aiohttp

# Load environment variables from .env file
load_dotenv()

# ============================================================
# CONFIGURATION LOADING
# ============================================================

def load_config():
    """Load configuration from config.json. Exit if not found."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    if not os.path.exists(config_path):
        print("=" * 60)
        print("  ❌ Configuration Not Found!")
        print("=" * 60)
        print()
        print("  config.json not found. Please run setup first:")
        print("    python setup.py")
        print()
        print("  Or copy config.example.json to config.json and edit it.")
        print("=" * 60)
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        return json.load(f)

# Load configuration
config = load_config()

# API Keys from environment
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Validate Discord token
if not DISCORD_TOKEN:
    print("❌ DISCORD_BOT_TOKEN not found in .env file!")
    print("   Run 'python setup.py' or add it to your .env file.")
    sys.exit(1)

# Channel IDs from config.json
channels = config.get("discord", {}).get("channels", {})
GENERAL_CHANNEL_ID = channels.get("general")
RESEARCH_CHANNEL_ID = channels.get("research")
BUILD_CHANNEL_ID = channels.get("build")
FINDINGS_CHANNEL_ID = channels.get("findings")
ARCHIVE_CHANNEL_ID = channels.get("archive")
TESTCASE_CHANNEL_ID = channels.get("testcase")
COMPLETED_CHANNEL_ID = channels.get("completed")
TASK_CHANNEL_ID = channels.get("task")

# Primary coordination channel
COORD_CHANNEL_ID = GENERAL_CHANNEL_ID

# Validate required channels
required_channels = ["general", "research", "build", "findings", "task", "completed"]
missing_channels = [ch for ch in required_channels if not channels.get(ch)]
if missing_channels:
    print(f"❌ Missing channel IDs in config.json: {', '.join(missing_channels)}")
    print("   Run 'python setup.py' to configure channels.")
    sys.exit(1)

# AI Model configuration (optional - uses defaults if not specified)
ai_models = config.get("ai_models", {})
RESEARCH_MODEL = ai_models.get("research", "claude-sonnet-4-20250514")
BUILD_MODEL = ai_models.get("build", "claude-sonnet-4-20250514")
GENERAL_MODEL = ai_models.get("general", "gpt-4")
CODE_MODEL = ai_models.get("code", "gemini-1.5-pro")
ROUTER_MODEL = ai_models.get("router", "gemini-1.5-flash")

# ============================================================
# INITIALIZE CLIENTS
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize AI clients (with graceful handling for missing keys)
claude_client = None
openai_client = None
gemini_client = None

if ANTHROPIC_API_KEY:
    claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)


class ProjectContext:
    """Loads context from local prompt files (no Discord channel fetching)"""
    
    PROMPTS_DIR = os.path.join(os.path.dirname(__file__), 'prompts')
    
    # Priority order for loading context files
    CONTEXT_FILES = [
        'canon.md',           # Primary source of truth
        'structure.md',       # Project structure
        'framing.md',         # Operational framing
        'timeline.md',        # Research timeline
        'roles.md',           # Responsibility split
        'discipline.md',      # Discipline rules
    ]
    
    @staticmethod
    def load_prompt_file(filename: str) -> str:
        """Load a single prompt file"""
        filepath = os.path.join(ProjectContext.PROMPTS_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return ""
    
    @staticmethod
    async def get_full_context(bot) -> str:
        """Load all context from local prompt files"""
        context_parts = []
        
        for filename in ProjectContext.CONTEXT_FILES:
            content = ProjectContext.load_prompt_file(filename)
            if content:
                context_parts.append(content)
        
        if context_parts:
            return "\n\n---\n\n".join(context_parts)
        return "No project context available."


class CenterAI:
    """Routes queries to appropriate specialist agents using Gemini (free tier)"""
    
    @staticmethod
    async def route_query(query: str) -> tuple[str, int]:
        """Determine which agent should handle the query using Gemini (free = $0 routing cost)"""
        
        if not gemini_client:
            return "research", RESEARCH_CHANNEL_ID
        
        prompt = f"""You are a routing AI. Classify this query as either:
- RESEARCH: questions about concepts, analysis, hypothesis testing, theory, reasoning
- BUILD: implementation, coding, technical setup, architecture, debugging

Query: {query}

Respond with just one word: RESEARCH or BUILD"""
        
        # Run Gemini in executor to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: gemini_client.models.generate_content(
                model=ROUTER_MODEL,
                contents=prompt
            )
        )
        
        decision = response.text.strip().upper()
        
        if "RESEARCH" in decision:
            return "research", RESEARCH_CHANNEL_ID
        else:
            return "build", BUILD_CHANNEL_ID


class ResearchAgent:
    """Handles research questions using Claude (best for reasoning/analysis)"""
    
    # Prompt file paths
    PROMPTS_DIR = os.path.join(os.path.dirname(__file__), 'prompts')
    
    @staticmethod
    def load_prompt(mode: str = 'core') -> str:
        """Load research prompt from file"""
        filename = 'research_hardmode.md' if mode == 'hardmode' else 'research_core.md'
        filepath = os.path.join(ResearchAgent.PROMPTS_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return "You are a research agent. Analyze the query carefully and provide thorough reasoning."
    
    @staticmethod
    async def process(query: str, context: list = None, project_context: str = None, mode: str = 'core') -> str:
        if not claude_client:
            return "❌ Claude (Anthropic) API key not configured. Add ANTHROPIC_API_KEY to your .env file."
        
        # Load the appropriate research prompt
        system_prompt = ResearchAgent.load_prompt(mode)
        
        messages = [{
            "role": "user",
            "content": f"""{system_prompt}

{project_context if project_context else ''}

Conversation context: {context if context else 'None'}

Query: {query}"""
        }]
        
        # Run Claude in executor to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: claude_client.messages.create(
                model=RESEARCH_MODEL,
                max_tokens=2000,
                messages=messages
            )
        )
        
        return response.content[0].text


class BuildAgent:
    """Handles implementation questions using Claude (strong for coding)"""
    
    SYSTEM_PROMPT = """You are a Build Agent (lab technician / engineer role).

## Your Purpose
Implement ONLY what Research AI has authorized. You execute, you do not decide.

## You ARE allowed to:
- Data ingestion
- Feature calculation (as specified)
- Experiment scripts
- Visualization
- Statistical testing
- Logging and archiving
- Reproducibility scaffolding

## You are NOT allowed to:
- Invent new features
- Redefine labels
- Add indicators not in the spec
- Adjust logic to "improve results"
- Reinterpret outcomes
- Make optimization suggestions

## Your outputs:
- Plots, tables, test statistics
- Failure evidence
- Raw results (NO interpretation)

## Kill Assumptions Gate (BEFORE implementing)
For any significant build request, FIRST list:
1. **Top 3 assumptions** this implementation depends on
2. **Cheap test** to falsify each assumption
3. **Canon check:** Are any assumptions already refuted in Canon?

If assumptions are untested, respond:
"⚠️ Before building, these assumptions need testing: [list]. Suggest running cheap tests first, or confirm you want to proceed at risk."

If the request requires inventing new features or redefining the experiment, respond:
"⚠️ This requires Research AI approval. Please get authorization first."
"""
    
    @staticmethod
    async def process(query: str, context: list = None, project_context: str = None) -> str:
        if not claude_client:
            return "❌ Claude (Anthropic) API key not configured. Add ANTHROPIC_API_KEY to your .env file."
        
        system_prompt = BuildAgent.SYSTEM_PROMPT
        if project_context:
            system_prompt += f"\n\n{project_context}"
        
        messages = [{
            "role": "user",
            "content": f"""{system_prompt}

Conversation context: {context if context else 'None'}

Query: {query}

Implement exactly what is requested. Do not add features or interpret results."""
        }]
        
        # Run Claude in executor for complex builds
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: claude_client.messages.create(
                model=BUILD_MODEL,
                max_tokens=2000,
                messages=messages
            )
        )
        
        return response.content[0].text


class GeminiAgent:
    """Third opinion agent using Gemini (free tier backup/tie-breaker)"""
    
    @staticmethod
    async def process(query: str, context: list = None, project_context: str = None) -> str:
        if not gemini_client:
            return "❌ Gemini API key not configured. Add GEMINI_API_KEY to your .env file."
        
        prompt = f"""You are an AI research assistant.

{project_context if project_context else ''}

Conversation context: {context if context else 'None'}

Query: {query}

Provide a helpful, balanced response. Reference the project context when relevant. Consider multiple perspectives."""
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: gemini_client.models.generate_content(
                model=CODE_MODEL,
                contents=prompt
            )
        )
        
        return response.text


class GeneralAgent:
    """Handles general questions using GPT-4 (cheaper than Claude for simple queries)"""
    
    @staticmethod
    async def process(query: str, context: list = None, project_context: str = None) -> str:
        if not openai_client:
            return "❌ OpenAI API key not configured. Add OPENAI_API_KEY to your .env file."
        
        system_prompt = """You are a helpful research assistant.
        
Be concise and practical. Reference project context when relevant.
For complex reasoning or deep analysis, suggest using !deep instead."""
        
        if project_context:
            system_prompt += f"\n\n{project_context}"
        
        messages = [{
            "role": "system",
            "content": system_prompt
        }, {
            "role": "user",
            "content": f"""Query: {query}"""
        }]
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: openai_client.chat.completions.create(
                model=GENERAL_MODEL,
                messages=messages,
                max_tokens=1500
            )
        )
        
        return response.choices[0].message.content


class SimpleCodeAgent:
    """Handles simple code tasks using Gemini (free tier)"""
    
    @staticmethod
    async def process(query: str, context: list = None, project_context: str = None) -> str:
        if not gemini_client:
            return "❌ Gemini API key not configured. Add GEMINI_API_KEY to your .env file."
        
        prompt = f"""You are a code assistant for Python data science projects.

Write simple, clean code. For complex implementations or architecture decisions, suggest using !build instead.

{project_context if project_context else ''}

Query: {query}

Provide working code with brief explanations."""
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: gemini_client.models.generate_content(
                model=CODE_MODEL,
                contents=prompt
            )
        )
        
        return response.text

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'')
    print(f'🤖 Multi-AI Research Bot Ready!')
    print(f'   Router: Explicit Commands (!ask, !deep, !gemini)')
    print(f'   Research: Claude {"✅" if claude_client else "❌"}')
    print(f'   Build: Claude {"✅" if claude_client else "❌"}')
    print(f'   General: GPT-4 {"✅" if openai_client else "❌"}')
    print(f'   Simple Code: Gemini {"✅" if gemini_client else "❌"}')
    print(f'   Backup: Gemini {"✅" if gemini_client else "❌"}')
    print(f'')
    print(f'Monitoring channels:')
    print(f'  Coordination: {COORD_CHANNEL_ID}')
    print(f'  Research: {RESEARCH_CHANNEL_ID}')
    print(f'  Build: {BUILD_CHANNEL_ID}')
    print(f'  Findings: {FINDINGS_CHANNEL_ID}')
    print(f'  Task: {TASK_CHANNEL_ID}')
    print(f'  Completed: {COMPLETED_CHANNEL_ID}')


@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Check for commands first
    if message.content.startswith('!'):
        await bot.process_commands(message)
        return
    
    # If mentioned, guide user to explicit commands
    if bot.user.mentioned_in(message):
        await message.channel.send(
            "👋 **Hi! Please use a command to ask me something:**\n\n"
            "• `!ask [question]` - General/Quick (GPT-4 $)\n"
            "• `!deep [question]` - Deep Research (Claude $$$)\n"
            "• `!code [request]` - Simple Code (Gemini FREE)\n"
            "• `!help_bot` - See all commands"
        )
        return


@bot.command(name='ask')
async def ask_general(ctx, *, query: str):
    """Ask GPT-4 for general questions (cheaper). Usage: !ask [question]"""
    
    async with ctx.typing():
        await ctx.send("💬 Asking GPT-4...")
        project_context = await ProjectContext.get_full_context(bot)
        
        response = await GeneralAgent.process(query, project_context=project_context)
        
        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
        for chunk in chunks:
            await ctx.send(chunk)


@bot.command(name='deep')
async def ask_deep(ctx, *, query: str):
    """Ask Claude for deep reasoning/analysis. Usage: !deep [question]"""
    
    async with ctx.typing():
        await ctx.send("🧠 Deep reasoning with Claude...")
        project_context = await ProjectContext.get_full_context(bot)
        
        response = await ResearchAgent.process(query, project_context=project_context, mode='core')
        research_channel = bot.get_channel(RESEARCH_CHANNEL_ID)
        
        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
        for i, chunk in enumerate(chunks):
            if i == 0:
                await research_channel.send(f"**Deep Research (Claude)** responding to: *{query[:100]}...*\n\n{chunk}")
            else:
                await research_channel.send(chunk)
        
        await ctx.send(f"✅ Claude's response posted in <#{RESEARCH_CHANNEL_ID}>")


@bot.command(name='research')
async def ask_research(ctx, *, query: str):
    """Alias for !deep. Ask Claude for deep reasoning. Usage: !research [question]"""
    await ask_deep(ctx, query=query)


@bot.command(name='hardmode')
async def ask_hardmode(ctx, *, query: str):
    """Stress-test an idea with aggressive skepticism. Usage: !hardmode [idea to scrutinize]"""
    
    async with ctx.typing():
        await ctx.send("🔥 **HARD MODE** - Loading project context and preparing critique...")
        project_context = await ProjectContext.get_full_context(bot)
        
        response = await ResearchAgent.process(query, project_context=project_context, mode='hardmode')
        research_channel = bot.get_channel(RESEARCH_CHANNEL_ID)
        
        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
        for i, chunk in enumerate(chunks):
            if i == 0:
                await research_channel.send(f"**🔥 HARD MODE CRITIQUE** of: *{query[:100]}...*\n\n{chunk}")
            else:
                await research_channel.send(chunk)
        
        await ctx.send(f"✅ Hard mode critique posted in <#{RESEARCH_CHANNEL_ID}>")


@bot.command(name='code')
async def ask_code(ctx, *, query: str):
    """Ask Gemini for simple code (FREE). Usage: !code [request]"""
    
    async with ctx.typing():
        await ctx.send("⚡ Quick code with Gemini (free)...")
        project_context = await ProjectContext.get_full_context(bot)
        
        response = await SimpleCodeAgent.process(query, project_context=project_context)
        
        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
        for chunk in chunks:
            await ctx.send(chunk)


@bot.command(name='build')
async def ask_build(ctx, *, query: str):
    """Ask Claude for complex implementation (with assumption gate). Usage: !build [question]"""
    
    async with ctx.typing():
        await ctx.send("🏗️ Building with Claude (checking assumptions)...")
        project_context = await ProjectContext.get_full_context(bot)
        
        response = await BuildAgent.process(query, project_context=project_context)
        build_channel = bot.get_channel(BUILD_CHANNEL_ID)
        
        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
        for i, chunk in enumerate(chunks):
            if i == 0:
                await build_channel.send(f"**Build Agent (Claude)** responding to: *{query[:100]}...*\n\n{chunk}")
            else:
                await build_channel.send(chunk)
        
        await ctx.send(f"✅ Claude's response posted in <#{BUILD_CHANNEL_ID}>")


@bot.command(name='gemini')
async def ask_gemini(ctx, *, query: str):
    """Ask Gemini directly with project context. Usage: !gemini [question]"""

    
    async with ctx.typing():
        await ctx.send("📚 Loading project context...")
        project_context = await ProjectContext.get_full_context(bot)
        
        response = await GeminiAgent.process(query, project_context=project_context)
        
        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
        for chunk in chunks:
            await ctx.send(chunk)


@bot.command(name='search')
async def web_search(ctx, *, query: str = None):
    """Web search using Perplexity (NOT YET AVAILABLE). Usage: !search [query]"""
    
    await ctx.send("⚠️ **Feature Not Available**\n\n"
                   "`!search` requires a Perplexity API key which is not configured.\n\n"
                   "**Alternatives:**\n"
                   "• Use `!ask` or `!deep` - Claude/GPT-4 have training data up to early 2024\n"
                   "• For current market data, use external sources and paste here")


@bot.command(name='context')
async def get_context(ctx, channel_name: str, limit: int = 20):
    """Get recent context from a channel. Usage: !context research 20"""
    
    channel_map = {
        'research': RESEARCH_CHANNEL_ID,
        'build': BUILD_CHANNEL_ID,
        'coord': COORD_CHANNEL_ID,
        'general': GENERAL_CHANNEL_ID,
        'findings': FINDINGS_CHANNEL_ID,
        'task': TASK_CHANNEL_ID,
        'completed': COMPLETED_CHANNEL_ID,
    }
    
    channel_id = channel_map.get(channel_name.lower())
    if not channel_id:
        await ctx.send(f"Unknown channel. Use: research, build, coord, general, findings, task, completed")
        return
    
    channel = bot.get_channel(channel_id)
    messages = []
    
    async for msg in channel.history(limit=limit):
        if msg.content:
            messages.append(f"**{msg.author.name}** ({msg.created_at.strftime('%Y-%m-%d %H:%M')}): {msg.content[:150]}")
    
    messages.reverse()
    response = "\n\n".join(messages)
    
    if not response:
        await ctx.send("No messages found in this channel.")
        return
    
    chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
    for chunk in chunks:
        await ctx.send(chunk)


@bot.command(name='crosscheck')
async def crosscheck(ctx, *, query: str):
    """Get responses from Claude AND GPT-4 with project context. Usage: !crosscheck [question]"""
    
    async with ctx.typing():
        await ctx.send("📚 Loading project context...")
        project_context = await ProjectContext.get_full_context(bot)
        
        await ctx.send(f"🔄 Querying Claude and GPT-4...")
        
        # Query both in parallel with project context
        claude_task = ResearchAgent.process(query, project_context=project_context)
        gpt_task = BuildAgent.process(query, project_context=project_context)
        
        claude_response, gpt_response = await asyncio.gather(claude_task, gpt_task)
        
        # Post comparison
        await ctx.send(f"**Cross-check:** *{query[:100]}...*\n\n"
                      f"**🔵 Claude's take:**\n{claude_response[:800]}\n\n"
                      f"**🟢 GPT-4's take:**\n{gpt_response[:800]}")


@bot.command(name='consensus')
async def consensus(ctx, *, query: str):
    """Get responses from ALL THREE AIs with project context. Usage: !consensus [question]"""
    
    async with ctx.typing():
        await ctx.send("📚 Loading project context...")
        project_context = await ProjectContext.get_full_context(bot)
        
        await ctx.send(f"🔄 Querying Claude, GPT-4, and Gemini...")
        
        # Query all three in parallel with project context
        claude_task = ResearchAgent.process(query, project_context=project_context)
        gpt_task = BuildAgent.process(query, project_context=project_context)
        gemini_task = GeminiAgent.process(query, project_context=project_context)
        
        claude_response, gpt_response, gemini_response = await asyncio.gather(
            claude_task, gpt_task, gemini_task
        )
        
        # Post to findings channel for record
        findings_channel = bot.get_channel(FINDINGS_CHANNEL_ID)
        await findings_channel.send(
            f"**🗳️ Consensus Query:** *{query[:100]}...*\n\n"
            f"**🔵 Claude:**\n{claude_response[:600]}\n\n"
            f"**🟢 GPT-4:**\n{gpt_response[:600]}\n\n"
            f"**🟡 Gemini:**\n{gemini_response[:600]}"
        )
        
        # Summary in current channel
        await ctx.send(
            f"**🗳️ Consensus Query:** *{query[:100]}...*\n\n"
            f"**🔵 Claude:**\n{claude_response[:500]}...\n\n"
            f"**🟢 GPT-4:**\n{gpt_response[:500]}...\n\n"
            f"**🟡 Gemini:**\n{gemini_response[:500]}...\n\n"
            f"📌 Full responses logged in <#{FINDINGS_CHANNEL_ID}>"
        )


@bot.command(name='log_finding')
async def log_finding(ctx, *, finding: str):
    """Log a key finding to #findings channel. Usage: !log_finding [your finding]"""
    
    findings_channel = bot.get_channel(FINDINGS_CHANNEL_ID)
    timestamp = discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    
    await findings_channel.send(f"📌 **Finding logged** ({timestamp})\n"
                               f"By: {ctx.author.name}\n\n"
                               f"{finding}")
    await ctx.send(f"✅ Finding logged to <#{FINDINGS_CHANNEL_ID}>")


@bot.command(name='channels')
async def list_channels(ctx):
    """List all available channels and their purposes"""
    
    channel_info = f"""**Available Channels:**
    
📋 **Organization:**
• <#{GENERAL_CHANNEL_ID}> - Main coordination (ask questions here)

🔬 **Research:**
• <#{RESEARCH_CHANNEL_ID}> - Research agent responses
• <#{FINDINGS_CHANNEL_ID}> - Key findings (use !log_finding)

🛠️ **Development:**
• <#{BUILD_CHANNEL_ID}> - Build agent responses
• <#{TESTCASE_CHANNEL_ID}> - Test cases

📊 **Task Management:**
• <#{TASK_CHANNEL_ID}> - Active tasks (use !task)
• <#{COMPLETED_CHANNEL_ID}> - Completed tasks (use !complete)

📁 **Archive:**
• <#{ARCHIVE_CHANNEL_ID}> - Archived content
    """
    
    await ctx.send(channel_info)


@bot.command(name='task')
async def create_task(ctx, *, description: str):
    """Create a new task in #task. Usage: !task [description]"""
    
    task_channel = bot.get_channel(TASK_CHANNEL_ID)
    timestamp = discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    
    # Create task message
    task_msg = await task_channel.send(
        f"📋 **New Task** ({timestamp})\n"
        f"Created by: {ctx.author.name}\n\n"
        f"{description}\n\n"
        f"Status: 🔵 **ACTIVE**"
    )
    
    await ctx.send(f"✅ Task created in <#{TASK_CHANNEL_ID}>\nTask ID: `{task_msg.id}`")


@bot.command(name='complete')
async def complete_task(ctx, task_id: int, *, result: str = "Completed"):
    """Mark a task as complete. Usage: !complete [task_id] [result]"""
    
    task_channel = bot.get_channel(TASK_CHANNEL_ID)
    completed_channel = bot.get_channel(COMPLETED_CHANNEL_ID)
    timestamp = discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    
    try:
        # Fetch the original task message
        task_msg = await task_channel.fetch_message(task_id)
        original_content = task_msg.content
        
        # Post to completed channel
        await completed_channel.send(
            f"✅ **Task Completed** ({timestamp})\n"
            f"Completed by: {ctx.author.name}\n\n"
            f"**Original Task:**\n{original_content}\n\n"
            f"**Result:** {result}"
        )
        
        # Delete from task channel
        await task_msg.delete()
        
        await ctx.send(f"✅ Task `{task_id}` moved to <#{COMPLETED_CHANNEL_ID}>")
        
    except discord.NotFound:
        await ctx.send(f"❌ Task `{task_id}` not found in <#{TASK_CHANNEL_ID}>")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command(name='help_bot')
async def help_bot(ctx):
    """Show all available bot commands"""
    
    help_text = """**🤖 Research Bot Commands:**

**General Questions (cheap):**
• `!ask [question]` - GPT-4 for quick answers ($)

**Deep Research (expensive, powerful):**
• `!deep [question]` - Claude for complex reasoning ($$$)
• `!research [question]` - Alias for !deep
• `!hardmode [question]` - Aggressive skepticism (Claude $$$)

**Code:**
• `!code [request]` - Gemini for simple code (FREE)
• `!build [request]` - Claude for complex implementation ($$$)

**Multi-AI:**
• `!crosscheck [question]` - Claude + GPT-4 comparison
• `!consensus [question]` - All 3 AIs (logged to #findings)
• `!gemini [question]` - Direct Gemini access (FREE)

**Task Management:**
• `!task [description]` - Create new task
• `!complete [task_id] [result]` - Mark task complete

**Utility:**
• `!context [channel] [limit]` - View recent messages
• `!log_finding [text]` - Log to #findings
• `!channels` - List all channels
• `!help_bot` - This help message

**Cost Guide:**
• FREE: Gemini (!code, !gemini)
• $: GPT-4 (!ask)
• $$$: Claude (!deep, !research, !hardmode, !build)
    """
    
    await ctx.send(help_text)


# Run the bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)