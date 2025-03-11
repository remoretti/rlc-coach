import os
from langchain_aws import BedrockChat
from dotenv import load_dotenv

load_dotenv()

def get_bedrock_llm():
    """Initialize AWS Bedrock LLM client."""
    # For Claude 3 Sonnet
    llm = BedrockChat(
        model_id="meta.llama3-3-70b-instruct-v1:0",
        region_name=os.getenv("AWS_REGION", "us-west-2"),
        model_kwargs={
            "temperature": 0.2,
            "max_tokens": 2000,
            "top_p": 0.9,
        }
    )
    return llm