import os
import discord
from discord.ext import commands
from anthropic import Anthropic
from openai import OpenAI

# Setup Discord bot
token = os.getenv('DISCORD_KEY')
anthropic_key = os.getenv('ANTHROPIC_KEY')
openai_key = os.getenv('OPENAI_KEY')
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
anthropic = Anthropic(api_key=anthropic_key)
openai = OpenAI(api_key=openai_key)
# Define available models
MODELS = {
    'sonnet': {'provider': 'anthropic', 'model': 'claude-3-5-sonnet-latest'},
    'haiku': {'provider': 'anthropic', 'model': 'claude-3-5-haiku-latest'},
    'gpt4': {'provider': 'openai', 'model': 'gpt-4'},
    'gpt4t': {'provider': 'openai', 'model': 'gpt-4-turbo'},
    'gpt4o': {'provider': 'openai', 'model': 'gpt-4o-mini'},
    'gpt4O': {'provider': 'openai', 'model': 'gpt-4o'},
    'gpto1': {'provider': 'openai', 'model': 'o1-mini'}
}

# Store conversation history and model choice
thread_configs = {}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='ct')
async def create_thread(ctx, thread_name, model: str = 'haiku'):
    """Creates a new thread with the specified name and model"""
    model = model.lower()
    if model not in MODELS:
        await ctx.send(f"Invalid model! Available models: {', '.join(MODELS.keys())}")
        return
    try:
        thread = await ctx.channel.create_thread(
            name=thread_name,
            type=discord.ChannelType.public_thread
        )
        thread_configs[thread.id] = {
            'model': MODELS[model],
            'history': []
        }
        await thread.send(f"Hello! I'm ready to chat using the {model} model. What would you like to discuss?")
    except discord.Forbidden:
        await ctx.send("I don't have permission to create threads!")
    except discord.HTTPException:
        await ctx.send("Failed to create thread!")

async def get_ai_response(model_config, messages):
    if model_config['provider'] == 'anthropic':
        response = anthropic.messages.create(
            model=model_config['model'],
            max_tokens=1000,
            messages=messages
        )
        return response.content[0].text
    elif model_config['provider'] == 'openai':
        # Convert message format for OpenAI
        openai_messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]
        response = openai.chat.completions.create(
            model=model_config['model'],
            messages=openai_messages,
            max_completion_tokens=1000
        )
        return response.choices[0].message.content

@bot.event
async def on_message(message):
    # Process commands first
    await bot.process_commands(message)
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    # Ignore messages that start with the command prefix
    if message.content.startswith(bot.command_prefix):
        return
    # Only respond in threads
    if isinstance(message.channel, discord.Thread):
        thread_id = message.channel.id
        # Check if thread is configured
        if thread_id not in thread_configs:
            thread_configs[thread_id] = {
                'model': MODELS['haiku'],  # Default to haiku
                'history': []
            }
        # Add user message to history
        thread_configs[thread_id]['history'].append({
            "role": "user",
            "content": message.content
        })
        try:
            async with message.channel.typing():
                # Get response from AI model
                ai_response = await get_ai_response(
                    thread_configs[thread_id]['model'],
                    thread_configs[thread_id]['history']
                )
                # Add AI response to history
                thread_configs[thread_id]['history'].append({
                    "role": "assistant",
                    "content": ai_response
                })
                # Keep history to last 10 messages to avoid token limits
                if len(thread_configs[thread_id]['history']) > 10:
                    thread_configs[thread_id]['history'] = thread_configs[thread_id]['history'][-10:]
                # Send response
                if len(ai_response) > 2000:
                    chunks = [ai_response[i:i+2000] for i in range(0, len(ai_response), 2000)]
                    for chunk in chunks:
                        await message.channel.send(chunk)
                else:
                    await message.channel.send(ai_response)
        except Exception as e:
            await message.channel.send(f"Sorry, I encountered an error: {str(e)}")

@bot.command(name='clearhistory')
async def clear_history(ctx):
    """Clears the conversation history for the current thread"""
    if not isinstance(ctx.channel, discord.Thread):
        await ctx.send("This command can only be used in threads!")
        return
    thread_id = ctx.channel.id
    if thread_id in thread_configs:
        thread_configs[thread_id]['history'] = []
        await ctx.send("Conversation history cleared!")

@bot.command(name='archivethread')
async def archive_thread(ctx):
    """Archives the current thread"""
    if not isinstance(ctx.channel, discord.Thread):
        await ctx.send("This command can only be used in threads!")
        return
    try:
        await ctx.channel.archive()
        await ctx.send("Thread archived!")
    except discord.Forbidden:
        await ctx.send("I don't have permission to archive this thread!")
    except discord.HTTPException:
        await ctx.send("Failed to archive thread!")

@bot.command(name='currentmodel')
async def current_model(ctx):
    """Shows the current model being used in the thread"""
    if not isinstance(ctx.channel, discord.Thread):
        await ctx.send("This command can only be used in threads!")
        return
    thread_id = ctx.channel.id
    if thread_id in thread_configs:
        model = next(k for k, v in MODELS.items() if v == thread_configs[thread_id]['model'])
        await ctx.send(f"Current model: {model}")
    else:
        await ctx.send("No model configured for this thread. Using default (haiku)")

bot.run(token)
