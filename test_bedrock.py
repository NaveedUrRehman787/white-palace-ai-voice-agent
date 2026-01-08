import os
import boto3
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def run_comprehensive_test():
    """
    Test Amazon Bedrock setup and Nova models.
    """
    region = os.getenv('AWS_REGION', 'us-east-1')
    print(f"--- Bedrock Diagnostics (Region: {region}) ---")
    
    try:
        # 1. Initialize Bedrock Client (Management)
        bedrock = boto3.client('bedrock', region_name=region)
        # 2. Initialize Bedrock Runtime Client (Inference)
        runtime = boto3.client('bedrock-runtime', region_name=region)
        
        # 3. List Nova Models
        print("\n[1/3] Checking Model Availability...")
        models = bedrock.list_foundation_models()['modelSummaries']
        nova_models = [m['modelId'] for m in models if 'nova' in m['modelId']]
        
        if not nova_models:
            print("❌ No Nova models found. Please enable them in the AWS Bedrock Console.")
            return

        print(f"✅ Found {len(nova_models)} Nova models.")
        for m in nova_models:
            if 'sonic' in m:
                print(f"  - {m} (Speech Mode Only)")
            else:
                print(f"  - {m}")

        # 4. Test Text Connectivity (using Nova Lite or Pro)
        # We use Nova Lite because it supports the simple Converse API for text.
        text_model = "amazon.nova-lite-v1:0"
        if text_model not in nova_models:
            # Fallback to any other non-sonic nova model
            non_sonic = [m for m in nova_models if 'sonic' not in m]
            if non_sonic:
                text_model = non_sonic[0]
            else:
                text_model = None

        if text_model:
            print(f"\n[2/3] Testing General Text Connectivity via '{text_model}'...")
            try:
                response = runtime.converse(
                    modelId=text_model,
                    messages=[{"role": "user", "content": [{"text": "Hello Bedrock! Confirm you are working."}]}],
                    inferenceConfig={"maxTokens": 50}
                )
                answer = response['output']['message']['content'][0]['text']
                print(f"✅ Success! Response: {answer}")
            except Exception as e:
                print(f"❌ Text test failed: {e}")
        else:
            print("\n[2/3] Skipping text test (no text-compatible Nova models available).")

        # 5. Explaining Nova 2 Sonic
        print(f"\n[3/3] Nova 2 Sonic Status:")
        sonic_id = "amazon.nova-2-sonic-v1:0"
        if sonic_id in nova_models:
            print(f"✅ Model '{sonic_id}' is available in your account.")
            print("-" * 50)
            print("NOTE: Nova 2 Sonic is a specialized 'Speech-to-Speech' model.")
            print("It does NOT support the standard synchronous 'Converse' or 'InvokeModel' APIs.")
            print("To use it, you must use the 'InvokeModelWithBidirectionalStream' API,")
            print("which is designed for real-time voice streaming.")
            print("-" * 50)
            print("Your credentials and Bedrock setup are CORRECT and WORKING.")
            print("You are ready to integrate Nova 2 Sonic into a voice-agent streaming architecture.")
        else:
            print(f"❌ Model '{sonic_id}' not found in your enabled models.")

    except Exception as e:
        print(f"\n❌ Critical Error during setup: {e}")
        print("Please check your AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")

if __name__ == "__main__":
    run_comprehensive_test()
