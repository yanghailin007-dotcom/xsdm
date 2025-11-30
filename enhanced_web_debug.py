"""
Enhanced Web Server with Detailed Debugging
"""

import sys
import os
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
os.chdir(BASE_DIR)

import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('web_debug.log', encoding='utf-8')
    ]
)

logger = logging.getLogger("DebugWebServer")

# Import project modules
from src.utils.logger import get_logger, Logger, LogLevel, setup_logging
from src.core.NovelGenerator import NovelGenerator
from config.config import CONFIG

# Configure custom logger to also write to web_debug.log
Logger.enable_file_logging("web_debug.log")
Logger.set_global_level(LogLevel.DEBUG)  # Enable all log levels

# Enable mock API
CONFIG["use_mock_api"] = True
logger.info("Mock API enabled for testing")
logger.info("Custom logger configured to write to web_debug.log")

# Create Flask app
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "web" / "templates"),
    static_folder=str(BASE_DIR / "web" / "static")
)
CORS(app)

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route('/api/start-generation', methods=['POST'])
def start_generation():
    """Start generation with detailed logging"""
    logger.info("="*60)
    logger.info("Received generation request")
    logger.info("="*60)

    try:
        # Log raw request data
        logger.debug(f"Request method: {request.method}")
        logger.debug(f"Request headers: {dict(request.headers)}")
        logger.debug(f"Request content-type: {request.content_type}")
        logger.debug(f"Request data (raw): {request.data}")

        # Parse JSON
        config = request.json
        logger.info(f"request.json type: {type(config)}")
        logger.info(f"request.json value: {config}")

        # Check if config is None or not a dict
        if config is None:
            logger.warning("request.json is None, using empty dict")
            config = {}
        elif isinstance(config, str):
            logger.warning(f"request.json is a string, attempting to parse: {config}")
            config = json.loads(config)
        elif not isinstance(config, dict):
            logger.error(f"request.json is unexpected type: {type(config)}")
            return jsonify({"success": False, "error": f"Invalid request data type: {type(config)}"}), 400

        # Log parsed config
        logger.info(f"Parsed config: {json.dumps(config, ensure_ascii=False, indent=2)}")

        # Extract fields with detailed logging
        title = config.get('title', 'Untitled')
        logger.debug(f"Title: {title}")

        synopsis = config.get('synopsis', '')
        logger.debug(f"Synopsis: {synopsis[:100]}...")

        core_setting = config.get('core_setting', '')
        logger.debug(f"Core setting: {core_setting[:100]}...")

        core_selling_points = config.get('core_selling_points', [])
        logger.debug(f"Core selling points: {core_selling_points}")

        total_chapters = config.get('total_chapters', 50)
        logger.debug(f"Total chapters: {total_chapters}")

        # Prepare creative seed with detailed logging
        logger.info("Preparing creative seed...")

        from src.utils.seed_utils import ensure_seed_dict

        if config.get("use_creative_file") and config.get("creative_seed"):
            logger.info("Using creative file mode")
            creative_data = config["creative_seed"]
            logger.debug(f"Creative seed type before ensure_seed_dict: {type(creative_data)}")

            creative_data = ensure_seed_dict(creative_data)
            logger.debug(f"Creative seed type after ensure_seed_dict: {type(creative_data)}")

            creative_seed = {
                "coreSetting": creative_data.get("coreSetting", ""),
                "coreSellingPoints": creative_data.get("coreSellingPoints", ""),
                "completeStoryline": creative_data.get("completeStoryline", {}),
                "targetAudience": creative_data.get("targetAudience", "web readers"),
                "novelTitle": config.get("title", "Untitled"),
                "themes": creative_data.get("themes", []),
                "writingStyle": creative_data.get("writingStyle", "modern web fiction")
            }
        else:
            logger.info("Using form input mode")
            constructed = {
                "coreSetting": core_setting,
                "coreSellingPoints": ", ".join(core_selling_points),
                "completeStoryline": {
                    "opening": f"Story begins with {synopsis}",
                    "development": "Story development",
                    "climax": "Story climax",
                    "ending": "Story ending"
                },
                "targetAudience": "web readers",
                "novelTitle": title,
                "themes": [],
                "writingStyle": "modern web fiction"
            }
            creative_seed = ensure_seed_dict(constructed)

        logger.info(f"Creative seed prepared: {json.dumps(creative_seed, ensure_ascii=False, indent=2)}")
        logger.debug(f"Creative seed type: {type(creative_seed)}")

        # Create generator
        logger.info("Creating NovelGenerator...")
        generator = NovelGenerator(CONFIG)
        logger.info("NovelGenerator created successfully")

        # Start generation (just 1 chapter for testing)
        test_chapters = 1
        logger.info(f"Starting generation of {test_chapters} chapter(s) for testing...")

        try:
            success = generator.full_auto_generation(
                creative_seed=creative_seed,
                total_chapters=test_chapters,
                overwrite=True
            )

            if success:
                logger.info("Generation completed successfully")
                novel_data = generator.novel_data

                return jsonify({
                    "success": True,
                    "message": f"Generated {test_chapters} chapter(s) successfully",
                    "novel_title": novel_data.get("novel_title", ""),
                    "chapters_generated": len(novel_data.get("generated_chapters", {}))
                })
            else:
                logger.error("="*60)
                logger.error("Generation returned False")
                logger.error("="*60)

                # Try to get error details from generator
                error_msg = "Generation failed"
                if hasattr(generator, 'last_error') and generator.last_error:
                    error_msg = generator.last_error
                    logger.error(f"Error from generator: {error_msg}")

                # Log novel_data state for debugging
                logger.error(f"Novel data state: {json.dumps(generator.novel_data.get('current_progress', {}), ensure_ascii=False, indent=2)}")

                return jsonify({"success": False, "error": error_msg}), 500

        except Exception as gen_error:
            logger.error("="*60)
            logger.error("Exception during full_auto_generation")
            logger.error("="*60)
            logger.error(f"Exception type: {type(gen_error).__name__}")
            logger.error(f"Exception message: {str(gen_error)}")
            import traceback
            logger.error("Full traceback:")
            logger.error(traceback.format_exc())

            return jsonify({
                "success": False,
                "error": f"{type(gen_error).__name__}: {str(gen_error)}",
                "traceback": traceback.format_exc()
            }), 500

    except AttributeError as e:
        logger.error(f"AttributeError: {e}")
        logger.error(f"This usually means a string was passed where a dict was expected")
        import traceback
        logger.error(traceback.format_exc())

        return jsonify({
            "success": False,
            "error": f"AttributeError: {str(e)}",
            "hint": "Check that all data is in correct format (dict not string)"
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/', methods=['GET'])
def index():
    """Serve index page"""
    return render_template('index.html')

if __name__ == '__main__':
    logger.info("="*60)
    logger.info("Starting Enhanced Debug Web Server")
    logger.info("="*60)
    logger.info(f"Base directory: {BASE_DIR}")
    logger.info(f"Template folder: {BASE_DIR / 'web' / 'templates'}")
    logger.info(f"Static folder: {BASE_DIR / 'web' / 'static'}")
    logger.info(f"Mock API enabled: {CONFIG.get('use_mock_api', False)}")
    logger.info("="*60)
    logger.info("Access at: http://localhost:5000")
    logger.info("Logs will be written to: web_debug.log")
    logger.info("="*60)

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False
    )
