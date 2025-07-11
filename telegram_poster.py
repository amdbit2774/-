import asyncio
import telegram # pip install python-telegram-bot
from telegram import Bot, Poll, Message # Import specific types
import json
import os
from pathlib import Path
import logging # <-- Add logging
import google.generativeai as genai # <-- Add Gemini imports
import fal_client # <-- Add fal.ai imports
import random # <-- Add random import
import requests # <-- Add requests for image download

# --- Logging Setup --- # <-- Add this section
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
# Get configuration from environment variables or fallback to hardcoded values
BOT_TOKEN = os.getenv("BOT_TOKEN", "7493745933:AAF8WpI25Q4I04htDsyowSzrUYbgmee5OVk")
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1002838702680")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyD48NkpKNjhZZM8BMuIerON0hsvzPl91Mk")
FAL_API_KEY = os.getenv("FAL_API_KEY", "cef62fb8-9a8c-443e-85cc-4f9805f6b853:25a71d66edc282c76dbb17dbe0712d29")

# Story settings
INITIAL_STORY_FILE = Path(__file__).parent / "initial_story.txt"
STORY_PROMPT_FILE = Path(__file__).parent / "story_prompt.txt"
POLL_PROMPT_FILE = Path(__file__).parent / "poll_prompt.txt"
CHARACTER_FILE = Path(__file__).parent / "Образ Патриции"

STATE_FILE = Path(__file__).parent / "story_state.json" # File to store story progress
POLL_QUESTION_TEMPLATE = "Что будет делать Патриция дальше?" # Default question for polls

# Gemini Settings # <-- Add this section
GEMINI_MODEL = "gemini-2.5-flash" # Gemini model for text generation
MAX_CONTEXT_CHARS = 15000 # Approximate limit to avoid huge API requests (adjust as needed)

# Image Generation Settings
FAL_MODEL = "fal-ai/flux/schnell" # fal.ai model for image generation
IMAGE_PROMPT_TEMPLATE = "Create a beautiful, detailed illustration for this story scene: {story_context}"

# --- End Configuration ---

# --- Gemini and fal.ai Client Initialization --- # <-- Add this section
gemini_client = None
fal_client_initialized = False

if GEMINI_API_KEY and GEMINI_API_KEY != "xxxx":
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_client = genai.GenerativeModel(GEMINI_MODEL)
        logging.info("Gemini client initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Gemini client: {e}")
        # gemini_client remains None
else:
    logging.warning("GEMINI_API_KEY not found or is placeholder. LLM features will be disabled.")

if FAL_API_KEY and FAL_API_KEY != "xxxx":
    try:
        # Set environment variable for fal_client
        os.environ["FAL_KEY"] = FAL_API_KEY
        fal_client_initialized = True
        logging.info("fal.ai client initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize fal.ai client: {e}")
        # fal_client_initialized remains False
else:
    logging.warning("FAL_API_KEY not found or is placeholder. Image generation will be disabled.")


# --- File Reading Functions --- #
def read_file_safe(file_path: Path, default_content: str = "") -> str:
    """Safely reads a file and returns its content or default."""
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    logging.info(f"Successfully read file: {file_path}")
                    return content
                else:
                    logging.warning(f"File {file_path} is empty.")
                    return default_content
        else:
            logging.error(f"File {file_path} does not exist.")
            return default_content
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return default_content

def get_initial_story() -> str:
    """Reads the initial story from file."""
    return read_file_safe(INITIAL_STORY_FILE, "История Патриции начинается...")

def get_story_prompt() -> str:
    """Reads the story generation prompt from file."""
    default_prompt = """
Ты - писатель. Напиши следующие три параграфа истории про Патрицию.
Предыдущая история: {story_context}
Выбор пользователя: '{user_choice}'
Напиши продолжение:
"""
    return read_file_safe(STORY_PROMPT_FILE, default_prompt)

def get_poll_prompt() -> str:
    """Reads the poll generation prompt from file."""
    default_prompt = """
Создай 4 варианта для опроса по истории:
{story_context}
Варианты:
1. [Вариант 1]
2. [Вариант 2]
3. [Вариант 3]
4. [Вариант 4]
"""
    return read_file_safe(POLL_PROMPT_FILE, default_prompt)



# --- State Management --- #
def load_state():
    """Loads the story state (current_story, last_poll_message_id) from the JSON file."""
    default_state = {"current_story": "", "last_poll_message_id": None}
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                # Ensure both keys exist, provide defaults if not
                if "current_story" not in state:
                    state["current_story"] = default_state["current_story"]
                if "last_poll_message_id" not in state:
                     state["last_poll_message_id"] = default_state["last_poll_message_id"]
                # Use logging instead of print
                logging.info(f"State loaded from {STATE_FILE}: {state}")
                return state
        except (json.JSONDecodeError, IOError) as e:
            # Use logging instead of print
            logging.error(f"Error loading state file {STATE_FILE}: {e}. Starting fresh.")
            return default_state
    else:
        # Use logging instead of print
        logging.info("State file not found. Starting fresh.")
        return default_state

def save_state(state):
    """Saves the story state to the JSON file."""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            # Ensure proper JSON formatting and Russian characters
            json.dump(state, f, ensure_ascii=False, indent=4)
        # Use logging instead of print
        logging.info(f"Story state saved to {STATE_FILE}: {state}")
    except IOError as e:
        # Use logging instead of print
        logging.error(f"Error saving state file {STATE_FILE}: {e}")

# --- Helper Function to Validate Configuration --- #
def validate_config():
    """Checks if the configuration values have been changed from placeholders."""
    valid = True
    if BOT_TOKEN == "YOUR_BOT_TOKEN" or not BOT_TOKEN:
        # Use logging instead of print
        logging.error("BOT_TOKEN is not set correctly.")
        valid = False
    # Basic check, refine channel ID validation if needed (e.g., check format)
    if not CHANNEL_ID or CHANNEL_ID == "@your_channel_username":
        logging.error("CHANNEL_ID is not set correctly.")
        valid = False
    # Add check for Gemini client initialization
    if not gemini_client:
         logging.warning("Gemini client is not initialized. Check GEMINI_API_KEY. LLM features disabled.")
         # Decide if this is critical. For now, allow running without it.
         # If LLM is essential, uncomment the next line:
         # valid = False
    
    # Add check for fal.ai client initialization
    if not fal_client_initialized:
         logging.warning("fal.ai client is not initialized. Check FAL_API_KEY. Image generation disabled.")
         # Image generation is optional, so we don't fail validation
    # Check if required files exist
    required_files = [INITIAL_STORY_FILE, STORY_PROMPT_FILE, POLL_PROMPT_FILE]
    for file_path in required_files:
        if not file_path.exists():
            logging.error(f"Required file missing: {file_path}")
            valid = False
    return valid

# --- Gemini and Image Generation Functions --- # # <-- NEW/REPLACED SECTION

def generate_story_continuation_gemini(current_story: str, user_choice: str) -> str | None:
    """Calls Gemini API to get the next story part.

    Returns:
        The new story part string, or None if API call fails.
    """
    if not gemini_client:
        logging.warning("Gemini client not available. Skipping story generation.")
        return "\n\n[Продолжение не сгенерировано - Gemini недоступен]" # Return placeholder text

    logging.info("Generating story continuation via Gemini...")

    # Truncate context if too long (simple tail truncation)
    truncated_story = current_story
    if len(current_story) > MAX_CONTEXT_CHARS:
        logging.warning(f"Current story context ({len(current_story)} chars) exceeds limit ({MAX_CONTEXT_CHARS}). Truncating.")
        truncated_story = current_story[-MAX_CONTEXT_CHARS:]

    # Load prompt from file and format it
    prompt_template = get_story_prompt()
    prompt = prompt_template.format(story_context=truncated_story, user_choice=user_choice)

    try:
        response = gemini_client.generate_content(prompt)
        
        if response.text and response.text.strip():
            logging.info("Gemini Story Part generated successfully.")
            # Add a newline for separation, ensure it's not just whitespace
            return "\n\n" + response.text.strip()
        else:
            logging.error("Gemini returned empty or invalid response.")
            return None

    except Exception as e:
        logging.error(f"Gemini API error during story generation: {e}", exc_info=True)
        return None

# COMMENTED OUT: Image generation disabled for now
# def generate_image_fal(story_context: str) -> str | None:
#     """Generates an image using fal.ai based on the story context.
# 
#     Returns:
#         The image URL, or None if generation fails.
#     """
#     if not fal_client_initialized:
#         logging.warning("fal.ai client not available. Skipping image generation.")
#         return None
# 
#     logging.info("Generating image via fal.ai...")
# 
#     # Truncate context if too long for image prompt
#     truncated_context = story_context[-1000:] if len(story_context) > 1000 else story_context
#     
#     # Create image prompt
#     image_prompt = IMAGE_PROMPT_TEMPLATE.format(story_context=truncated_context)
#     
#     try:
#         handler = fal_client.submit(
#             FAL_MODEL,
#             arguments={
#                 "prompt": image_prompt,
#                 "image_size": "landscape_16_9",
#                 "num_inference_steps": 4,
#                 "num_images": 1,
#                 "enable_safety_checker": True
#             }
#         )
#         
#         result = handler.get()
#         
#         if result and "images" in result and len(result["images"]) > 0:
#             image_url = result["images"][0]["url"]
#             logging.info(f"Image generated successfully: {image_url}")
#             return image_url
#         else:
#             logging.error("fal.ai returned empty or invalid response.")
#             return None
# 
#     except Exception as e:
#         logging.error(f"fal.ai API error during image generation: {e}", exc_info=True)
#         return None

def generate_image_fal(story_context: str) -> str | None:
    """Image generation disabled. Always returns None."""
    logging.info("Image generation is disabled.")
    return None

def generate_poll_options_gemini(full_story_context: str) -> list[str] | None:
    """Calls Gemini API to get 4 poll options.

    Returns:
        A list of 4 distinct poll options (max 90 chars each), or None if API call fails.
    """
    if not gemini_client:
        logging.warning("Gemini client not available. Skipping poll option generation.")
        # Return placeholder options if needed for testing w/o API key
        return [
            "Placeholder Option 1?",
            "Placeholder Option 2!",
            "Placeholder Option 3...",
            "Placeholder Option 4."
        ]

    logging.info("Generating poll options via Gemini...")

    # Truncate context if too long
    truncated_context = full_story_context[-MAX_CONTEXT_CHARS:]

    # Load prompt from file and format it
    prompt_template = get_poll_prompt()
    prompt = prompt_template.format(story_context=truncated_context)

    try:
        response = gemini_client.generate_content(prompt)
        
        if response.text and response.text.strip():
            # Parse the response to extract options
            lines = response.text.strip().split('\n')
            options = []
            for line in lines:
                line = line.strip()
                if line and (line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.startswith('4.')):
                    option = line[2:].strip()[:90]  # Remove numbering and truncate
                    if option:
                        options.append(option)
            
            if len(options) == 4:
                logging.info(f"Gemini Poll Options generated: {options}")
                return options
            else:
                logging.error(f"Gemini returned {len(options)} options, expected 4.")
                return None
        else:
            logging.error("Gemini returned empty or invalid response.")
            return None

    except Exception as e:
        logging.error(f"Gemini API error during poll option generation: {e}", exc_info=True)
        return None

# --- Core Story Logic --- #
async def get_poll_winner(bot: Bot, chat_id: str | int, message_id: int) -> str | None:
    """Stops the specified poll and returns the winning option text, or None if no winner/error."""
    if message_id is None:
        logging.warning("No message ID provided to get_poll_winner.")
        return None

    logging.info(f"Attempting to stop poll (Message ID: {message_id})...")
    try:
        updated_poll: Poll = await bot.stop_poll(chat_id=chat_id, message_id=message_id)
        logging.info(f"Poll stopped successfully (Message ID: {message_id}).")

        # Analyze poll results
        if not updated_poll.options:
            logging.warning("Poll has no options.")
            return None

        # Get vote counts for each option
        vote_counts = [(option.text, option.voter_count) for option in updated_poll.options]
        total_votes = sum(count for _, count in vote_counts)
        
        # Log detailed results
        logging.info(f"Poll results (Total votes: {total_votes}):")
        for i, (option_text, votes) in enumerate(vote_counts, 1):
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            logging.info(f"  {i}. '{option_text}': {votes} votes ({percentage:.1f}%)")

        # Determine winner
        if total_votes == 0:
            logging.info("Poll closed with no votes. Randomly selecting a winner.")
            random_winner = random.choice(updated_poll.options)
            winner_text = random_winner.text
            logging.info(f"🎲 Random winner selected: '{winner_text}'")
            return winner_text
        
        # Find maximum votes
        max_votes = max(count for _, count in vote_counts)
        winners = [text for text, count in vote_counts if count == max_votes]
        
        if len(winners) == 1:
            winner_text = winners[0]
            percentage = (max_votes / total_votes * 100) if total_votes > 0 else 0
            logging.info(f"🏆 Clear winner: '{winner_text}' with {max_votes} votes ({percentage:.1f}%)")
            return winner_text
        else:
            # Multiple winners (tie)
            logging.info(f"🤝 Tie detected: {len(winners)} options with {max_votes} votes each")
            tied_options = ', '.join(f"'{opt}'" for opt in winners)
            logging.info(f"   Tied options: {tied_options}")
            
            # Randomly select from tied options
            winner_text = random.choice(winners)
            logging.info(f"🎲 Random selection from tied options: '{winner_text}'")
            return winner_text

    except telegram.error.BadRequest as e:
        err_text = str(e).lower()
        if "poll has already been closed" in err_text:
            # Use logging
            logging.info(f"Poll (ID: {message_id}) was already closed. Attempting to fetch results directly (Currently not reliably implemented).", exc_info=True)
            # NOTE: Reliably fetching results for already-closed polls is complex and often
            # requires storing poll data yourself or using user bots/MTProto.
            # For now, we cannot reliably get the winner in this state.
            return None
        elif "message to stop poll not found" in err_text:
            # Use logging
            logging.error(f"Could not find the poll message to stop (ID: {message_id}). Was it deleted?")
            return None
        else:
            # Use logging
            logging.error(f"Error stopping poll (BadRequest - ID: {message_id}): {e}")
            return None # Treat other bad requests as failure
    except telegram.error.Forbidden as e:
         # Use logging
         logging.error(f"Error stopping poll (Forbidden - ID: {message_id}): {e}. Bot lacks permissions?", exc_info=True)
         raise # Re-raise permission errors as they need fixing
    except telegram.error.TelegramError as e:
        # Errors during story/poll sending (get_poll_winner handles its own)
        # Use logging
        logging.error(f"Error stopping poll (ID: {message_id}): {e}", exc_info=True)
        return None # Treat other telegram errors as failure



# --- Main Async Function --- #
async def run_story_step():
    """Performs one step: loads state, gets winner, generates next step, posts, saves state."""

    if not validate_config():
        logging.critical("Configuration errors found. Exiting.")
        return

    logging.info("=" * 60)
    logging.info("🤖 STARTING NEW STORY STEP")
    logging.info(f"🕒 Timestamp: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("=" * 60)
    
    state = load_state()
    current_story = state.get("current_story", "")
    last_poll_message_id = state.get("last_poll_message_id")
    
    # Log current state
    story_length = len(current_story) if current_story else 0
    logging.info(f"📊 Current state: Story length: {story_length} chars, Last poll ID: {last_poll_message_id}")

    # Use logging
    logging.info("Initializing Telegram bot...")
    bot = Bot(token=BOT_TOKEN)

    next_prompt: str | None = None
    story_just_started: bool = False
    new_poll_message_id: int | None = None

    # Wrap core logic in try/except to catch API errors and prevent inconsistent state saving
    # Note: get_poll_winner already handles its own Telegram errors
    try:
        # 1. Get Poll Winner (if applicable)
        if last_poll_message_id:
            logging.info(f"📊 Checking results for previous poll (ID: {last_poll_message_id})")
            poll_winner = await get_poll_winner(bot, CHANNEL_ID, last_poll_message_id)
            if poll_winner:
                next_prompt = poll_winner
                logging.info(f"🎯 Poll winner will guide story: '{poll_winner}'")
            else:
                logging.warning(f"⚠️  No winner determined from poll (ID: {last_poll_message_id}). Using fallback.")
                # If story exists, maybe we want a different fallback? For now, reuse initial.
                next_prompt = "Продолжай как считаешь нужным." # Fallback if poll fails or has no winner
        else:
            logging.info("🆕 No previous poll found. Starting new story.")
            next_prompt = None  # Will use initial story

        # 2. Generate & Post Story Part
        new_story_part = None # Initialize to None
        if not current_story: # Is this the very first run?
            # Use logging
            logging.info("No existing story found. Posting initial story.")
            # We don't need LLM for the very first post
            message_to_send = get_initial_story()
            current_story = message_to_send # Initialize story state
            story_just_started = True
            # Use logging
            logging.info(f"Sending initial story part to channel {CHANNEL_ID}...")
            
            # Generate image for the initial story part (disabled)
            image_url = generate_image_fal(message_to_send)
            
            try:
                if image_url:
                    # Send message with image
                    await bot.send_photo(
                        chat_id=CHANNEL_ID, 
                        photo=image_url,
                        caption=message_to_send,
                        parse_mode='HTML'
                    )
                    logging.info("Initial story part sent with image.")
                else:
                    # Send message without image
                    await bot.send_message(chat_id=CHANNEL_ID, text=message_to_send)
                    logging.info("Initial story part sent without image.")
            except telegram.error.TelegramError as e:
                logging.error(f"Failed to send initial story part: {e}", exc_info=True)
                raise # Re-raise to prevent inconsistent state
            # No need to assign to new_story_part here, as it's the whole story
        else:
            # It's a continuation run
            story_just_started = False
            if not next_prompt:
                 # Use logging
                 logging.error("No prompt available for continuation (should not happen!). Using fallback.")
                 next_prompt = "Продолжай как считаешь нужным."

            # Use logging
            logging.info(f"Generating story continuation based on: '{next_prompt}'")
            # *** CALL ACTUAL OPENAI FUNCTION ***
            new_story_part = generate_story_continuation_gemini(current_story, next_prompt)

            if new_story_part and new_story_part.strip(): # Check if LLM returned something valid
                 logging.info(f"📤 Sending new story part to channel {CHANNEL_ID}...")
                 
                 # Generate image for the story part
                 logging.info("🎨 Generating image for story part...")
                 image_url = generate_image_fal(new_story_part)
                 
                 try:
                     if image_url:
                         # Send message with image
                         await bot.send_photo(
                             chat_id=CHANNEL_ID, 
                             photo=image_url,
                             caption=new_story_part,
                             parse_mode='HTML'
                         )
                         logging.info("✅ Story part sent with image")
                     else:
                         # Send message without image
                         await bot.send_message(chat_id=CHANNEL_ID, text=new_story_part)
                         logging.info("✅ Story part sent (no image)")
                     
                     current_story += new_story_part # Append *only* if successfully generated and sent
                     logging.info("Story context updated.")
                 except telegram.error.TelegramError as e:
                     logging.error(f"Failed to send new story part: {e}", exc_info=True)
                     raise # Re-raise to prevent inconsistent state
            else:
                 # *** LLM CALL FAILED OR RETURNED EMPTY ***
                 # Use logging
                 logging.error("Story continuation failed or returned empty. Story not updated. Interrupting step.")
                 # Prevent poll generation if story failed
                 raise RuntimeError("LLM failed to generate story continuation.") # Raise a generic error

        # 3. Generate and Post Poll
        # Use logging
        logging.info("Generating poll options based on current story...")
        # *** CALL ACTUAL OPENAI FUNCTION ***
        poll_options = generate_poll_options_gemini(current_story)

        if not poll_options or len(poll_options) != 4:
             # Use logging
             logging.error("Could not generate valid poll options. Skipping poll posting.")
             new_poll_message_id = None # Ensure state reflects poll failure
        else:
            # Ensure options respect Telegram's 90-character limit
            truncated_options = [opt[:90] for opt in poll_options]
            logging.info(f"Generated {len(truncated_options)} poll options (truncated if needed). First option: '{truncated_options[0]}'...")
            try:
                sent_poll_message: Message = await bot.send_poll(
                    chat_id=CHANNEL_ID,
                    question=POLL_QUESTION_TEMPLATE,
                    options=truncated_options, # Use truncated options
                    is_anonymous=True, # Default and recommended for stories
                    # open_period=... # Consider adding a time limit? e.g., 86400 for 24h
                )
                new_poll_message_id = sent_poll_message.message_id
                logging.info(f"New poll sent (Message ID: {new_poll_message_id}).")
            except telegram.error.TelegramError as poll_error:
                 # Use logging
                 logging.error(f"Error sending poll: {poll_error}. Skipping poll posting.", exc_info=True)
                 new_poll_message_id = None # Record poll failure

        # 4. Save State for Next Run (Only if this point is reached without errors)
        state_to_save = {
            "current_story": current_story,
            "last_poll_message_id": new_poll_message_id
        }
        save_state(state_to_save)
        
        # Success logging
        final_story_length = len(current_story)
        logging.info("=" * 60)
        logging.info("✅ STORY STEP COMPLETED SUCCESSFULLY")
        logging.info(f"📈 Final story length: {final_story_length} chars")
        logging.info(f"🗳️  New poll ID: {new_poll_message_id}")
        logging.info(f"⏰ Next run in 2 hours")
        logging.info("=" * 60)

    # Catch specific API errors or general exceptions from the core logic block
    except telegram.error.TelegramError as e:
        # Errors during story/poll sending
        logging.error(f"\n--- A Telegram API Error Occurred During Story Step --- ")
        logging.error(f"Error message: {e}")
        logging.error("Script interrupted due to Telegram API error. State NOT saved for this run.")
        # No return here
    except RuntimeError as e:
        # Catch the custom error raised for LLM failure
        logging.error(f"\n--- A Runtime Error Occurred During Story Step --- ")
        logging.error(f"Error message: {e}")
        logging.error("Script interrupted. State NOT saved for this run.")
    except Exception as e:
        # Use logging
        logging.error(f"\n--- An Unexpected Error Occurred During Story Step --- ")
        logging.error(f"Error message: {e}", exc_info=True)
        logging.error("Script interrupted due to unexpected error. State NOT saved for this run.")
        # No return here
    finally:
        logging.info("🏁 Story step execution finished")
        logging.info("=" * 60)
        # Optional: Add cleanup here if needed


# --- Run the Script --- #
if __name__ == "__main__":
    # Use logging
    logging.info("Script execution started.")

    # Validate essential config before attempting async execution
    if not validate_config():
         logging.critical("Configuration validation failed. Please check BOT_TOKEN, CHANNEL_ID, and GEMINI_API_KEY (if used). Exiting.")
    elif not gemini_client:
        logging.warning("Gemini client not initialized. LLM features will use placeholders or fail. Proceeding...")
        asyncio.run(run_story_step())
    else:
        logging.info("Configuration validated. Running async story step.")
        asyncio.run(run_story_step())

    logging.info("Script execution finished.")
