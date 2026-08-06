"""AWS Lambda entry point for API Gateway."""

from mangum import Mangum

from app.main import app

handler = Mangum(app, lifespan="off")
