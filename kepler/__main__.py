import uvicorn

from kepler.config import Config

if __name__ == "__main__":
    config = Config()
    uvicorn.run(
        "kepler.web.app:create_app",
        host=config.host,
        port=config.port,
        factory=True,
    )
