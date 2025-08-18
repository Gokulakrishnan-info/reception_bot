#!/usr/bin/env python3
"""
Main execution file for Modular AI Bot
Starts the AI reception bot with proper initialization
"""

import sys
import threading
import logging
from ai_reception_bot import AIReceptionBot
from aws_config import setup_aws_credentials

def main():
    """Main execution function"""
    print("🤖 AI Reception Bot - Jarvis")
    print("Features:")
    print("  🔑 Wake word: 'Hey Jarvis'")
    print("  👤 Facial recognition with DeepFace")
    print("  🤖 AWS Bedrock Nova Lite-powered conversation")
    print("  📅 Calendar integration (placeholder)")
    print("  👥 Employee directory lookup")
    print("  🗣️ Voice interface")
    print("\nChecking AWS Bedrock configuration...")
    
    # Check AWS credentials before starting
    if not setup_aws_credentials():
        print("❌ AWS Bedrock not configured. Please set up your AWS credentials.")
        print("Run: python aws_config.py for setup instructions.")
        return
    
    print("✅ AWS Bedrock configured successfully!")
    print("\nStarting Jarvis...")
    
    bot = AIReceptionBot()

    # If PyQt6 UI is available, run the UI event loop on the main thread
    # and move the bot logic to a background thread. This ensures the
    # avatar window is responsive and visible.
    try:
        if hasattr(bot, 'avatar_agent') and hasattr(bot.avatar_agent, 'app') and bot.avatar_agent.app is not None:
            print("🚀 Starting PyQt6 avatar interface...")
            # Create a signal to stop the bot when UI closes
            bot.avatar_agent.window.destroyed.connect(lambda: setattr(bot, 'should_stop', True))
            
            # Start bot in background thread
            worker = threading.Thread(target=bot.run, daemon=True)
            worker.start()
            
            # Run Qt event loop in main thread (blocks until window is closed)
            print("🖥️ Avatar interface is now visible. The bot is running in the background.")
            print("💡 You can now say 'Hey Jarvis' to activate the bot!")
            bot.avatar_agent.app.exec()
            
            # After UI closes, stop the worker thread gracefully
            if worker.is_alive():
                print("🔄 Shutting down bot...")
                bot.should_stop = True
                worker.join(timeout=2.0)
                if worker.is_alive():
                    print("⚠️ Bot thread did not stop gracefully")
        else:
            # Fallback: no PyQt6, run normally (Tkinter runs in its own thread)
            print("🔄 PyQt6 not available, using Tkinter fallback...")
            bot.run()
    except Exception as e:
        logging.warning(f"UI loop error, running bot without PyQt6 UI: {e}")
        print(f"⚠️ UI error: {e}")
        print("🔄 Falling back to console mode...")
        bot.run()

if __name__ == "__main__":
    main()
