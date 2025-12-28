#!/usr/bin/env python3
"""
Interactive Setup Wizard for Multi-AI Research Bot
Run this before starting the bot for the first time.
"""

import os
import json
import sys

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("=" * 60)
    print("  🤖 Multi-AI Research Bot - Setup Wizard")
    print("=" * 60)
    print()

def get_input(prompt, required=True, default=None):
    """Get user input with optional default value."""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    while True:
        value = input(prompt).strip()
        if not value and default:
            return default
        if not value and required:
            print("  ⚠️  This field is required.")
            continue
        return value

def get_channel_id(name):
    """Get and validate a Discord channel ID."""
    while True:
        value = input(f"  {name} Channel ID: ").strip()
        if not value:
            print("    ⚠️  Channel ID is required.")
            continue
        try:
            int(value)
            return int(value)
        except ValueError:
            print("    ⚠️  Channel ID must be a number.")
            continue

def main():
    clear_screen()
    print_header()
    
    print("Welcome! This wizard will help you configure your Research Bot.\n")
    print("You'll need:")
    print("  • Discord Bot Token (from Discord Developer Portal)")
    print("  • At least one AI API key (Anthropic, OpenAI, or Gemini)")
    print("  • Discord Channel IDs for your server\n")
    
    input("Press Enter to continue...")
    
    # ========== API KEYS ==========
    clear_screen()
    print_header()
    print("STEP 1: API Keys\n")
    print("Get your API keys from:")
    print("  • Discord: https://discord.com/developers/applications")
    print("  • Anthropic: https://console.anthropic.com/")
    print("  • OpenAI: https://platform.openai.com/")
    print("  • Gemini: https://aistudio.google.com/app/apikey (FREE!)\n")
    
    discord_token = get_input("Discord Bot Token")
    anthropic_key = get_input("Anthropic API Key (for Claude)", required=False) or ""
    openai_key = get_input("OpenAI API Key (for GPT-4)", required=False) or ""
    gemini_key = get_input("Gemini API Key (FREE)", required=False) or ""
    
    if not any([anthropic_key, openai_key, gemini_key]):
        print("\n⚠️  Warning: No AI API keys provided. Some commands won't work.")
        input("Press Enter to continue anyway...")
    
    # ========== CHANNEL IDS ==========
    clear_screen()
    print_header()
    print("STEP 2: Discord Channel IDs\n")
    print("To get a channel ID:")
    print("  1. Enable Developer Mode in Discord (User Settings > App Settings > Advanced)")
    print("  2. Right-click any channel > Copy Channel ID\n")
    print("Enter the Channel IDs for your server:\n")
    
    channels = {
        "general": get_channel_id("General/Coordination"),
        "research": get_channel_id("Research"),
        "build": get_channel_id("Build"),
        "findings": get_channel_id("Findings"),
        "archive": get_channel_id("Archive"),
        "testcase": get_channel_id("Test Cases"),
        "completed": get_channel_id("Completed Tasks"),
        "task": get_channel_id("Active Tasks"),
    }
    
    # ========== SAVE CONFIG ==========
    clear_screen()
    print_header()
    print("STEP 3: Saving Configuration\n")
    
    # Create .env file
    env_content = f"""# Discord Bot Token
DISCORD_BOT_TOKEN={discord_token}

# API Keys
ANTHROPIC_API_KEY={anthropic_key}
OPENAI_API_KEY={openai_key}
GEMINI_API_KEY={gemini_key}
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    print("✅ Created .env file")
    
    # Create config.json
    config = {
        "discord": {
            "channels": channels
        },
        "ai_models": {
            "research": "claude-sonnet-4-20250514",
            "build": "claude-sonnet-4-20250514",
            "general": "gpt-4",
            "code": "gemini-1.5-pro",
            "router": "gemini-1.5-flash"
        }
    }
    
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)
    print("✅ Created config.json file")
    
    # ========== PROMPTS ==========
    print()
    prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
    templates_dir = os.path.join(prompts_dir, 'templates')
    
    if os.path.exists(templates_dir):
        print("📝 Template prompts available in prompts/templates/")
        print("   Copy and customize them for your research domain.")
    
    # ========== DONE ==========
    print()
    print("=" * 60)
    print("  ✅ Setup Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Customize your prompts in the prompts/ folder")
    print("  2. Run: python main.py")
    print()
    print("For help, see README.md or contact: yjchoongwork@gmail.com")
    print()

if __name__ == "__main__":
    main()
