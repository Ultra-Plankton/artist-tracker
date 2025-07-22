<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Music Updater Project Instructions

This is a Python project for tracking music artists and their releases, with planned integrations for:

## Project Structure
- `main.py` - Main artist tracker application
- `config.py` - Configuration settings for APIs
- `requirements.txt` - Python dependencies

## Planned Features
1. **Artist Tracking** - Track favorite artists (✅ Implemented)
2. **Spotify API Integration** - Pull latest releases using Spotify Web API
3. **Discord Bot Integration** - Send notifications about new releases
4. **Data Persistence** - Save artist data to file/database

## Code Style Guidelines
- Use Python 3.8+ features
- Follow PEP 8 style guidelines
- Add type hints where appropriate
- Include docstrings for all functions and classes
- Keep functions small and focused
- Use meaningful variable names

## API Integration Notes
- Spotify API requires client credentials flow
- Discord.py library for bot functionality
- Consider rate limiting for API calls
- Store sensitive credentials in environment variables

## Development Approach
- Start simple and expand gradually
- Test each feature before moving to the next
- Keep the core functionality working while adding features
- Use modular design for easy extension
