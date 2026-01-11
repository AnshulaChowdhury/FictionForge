# AWS Bedrock Setup Duplication & Sentence Transformer Integration
## Technical Documentation for Consciousness Trilogy App

**Created:** November 2, 2025  
**Purpose:** Duplicate existing AWS Lambda + API Gateway + Bedrock setup and integrate sentence-transformers for RAG embeddings

---

## Table of Contents

1. [AWS Infrastructure Duplication](#1-aws-infrastructure-duplication)
2. [Sentence Transformer Setup](#2-sentence-transformer-setup)
3. [Epic 5A Integration (Character RAG)](#3-epic-5a-integration-character-rag)
4. [Epic 5B Integration (World Rule RAG)](#4-epic-5b-integration-world-rule-rag)
5. [Testing & Validation](#5-testing--validation)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. AWS Infrastructure Duplication

### 1.1 Prerequisites

**Required Information from Existing Setup:**
- Current Lambda function name: `FictionForgeLLM`
- Current Lambda function ARN: `arn:aws:lambda:YOUR_REGION:YOUR_AWS_ACCOUNT_ID:function:YOUR_FUNCTION_NAME`
- AWS Region: `ca-central-1`
- IAM Role with Bedrock permissions
- API Gateway ID (if reusing)

**Tools Needed:**
- AWS CLI installed and configured
- AWS Console access
- Python 3.11+ (to match Lambda runtime)

### 1.2 Export Existing Lambda Configuration

```bash
# Export function configuration
aws lambda get-function \
  --function-name FictionForgeLLM \
  --region ca-central-1 \
  --query 'Configuration' > lambda_config.json

# Download the deployment package
aws lambda get-function \
  --function-name FictionForgeLLM \
  --region ca-central-1 \
  --query 'Code.Location' \
  --output text | xargs curl -o function.zip
```

### 1.3 Review Current Configuration

```bash
# Extract and inspect the code
unzip function.zip -d lambda_function/
cat lambda_config.json | jq '.Environment.Variables'
```

**Key Configuration Elements to Note:**
- Runtime (likely `python3.11` or `python3.12`)
- Memory allocation (e.g., 1024 MB)
- Timeout (e.g., 30 seconds)
- Environment variables (Bedrock model names, region settings)
- IAM Role ARN

### 1.4 Create New IAM Role for Consciousness Trilogy App

```bash
# Create trust policy document
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the IAM role
aws iam create-role \
  --role-name ConsciousnessTrilogyLambdaRole \
  --assume-role-policy-document file://trust-policy.json

# Attach managed policies
aws iam attach-role-policy \
  --role-name ConsciousnessTrilogyLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create custom Bedrock policy
cat > bedrock-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:ca-central-1::foundation-model/mistral.mistral-7b-instruct-v0:2",
        "arn:aws:bedrock:ca-central-1::foundation-model/mistral.mistral-large-2402-v1:0"
      ]
    }
  ]
}
EOF

# Attach custom Bedrock policy
aws iam put-role-policy \
  --role-name ConsciousnessTrilogyLambdaRole \
  --policy-name BedrockAccessPolicy \
  --policy-document file://bedrock-policy.json
```

### 1.5 Create New Lambda Function

**Option A: Using AWS CLI**

```bash
# Create new Lambda function
aws lambda create-function \
  --function-name ConsciousnessTrilogyBedrockAPI \
  --runtime python3.11 \
  --role arn:aws:iam::<YOUR_ACCOUNT_ID>:role/ConsciousnessTrilogyLambdaRole \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 60 \
  --memory-size 1024 \
  --region ca-central-1 \
  --environment Variables="{
    BEDROCK_MODEL_ID=mistral.mistral-7b-instruct-v0:2,
    BEDROCK_REGION=ca-central-1,
    MAX_TOKENS=2048,
    TEMPERATURE=0.7
  }"
```

**Option B: Using AWS Console (Recommended for First Time)**

1. Navigate to AWS Lambda Console
2. Click "Create function"
3. Choose "Author from scratch"
4. Function name: `ConsciousnessTrilogyBedrockAPI`
5. Runtime: Python 3.11
6. Architecture: x86_64
7. Execution role: Use existing role → `ConsciousnessTrilogyLambdaRole`
8. Click "Create function"
9. Upload `function.zip` in Code source section
10. Configure environment variables:
   ```
   BEDROCK_MODEL_ID = mistral.mistral-7b-instruct-v0:2
   BEDROCK_REGION = ca-central-1
   MAX_TOKENS = 2048
   TEMPERATURE = 0.7
   ```
11. Configuration → General configuration:
    - Memory: 1024 MB
    - Timeout: 1 min

### 1.6 Lambda Function Code Template

```python
# lambda_function.py
import json
import boto3
import os

# Initialize Bedrock client
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name=os.environ.get('BEDROCK_REGION', 'ca-central-1')
)

def lambda_handler(event, context):
    """
    Lambda handler for Consciousness Trilogy Bedrock API
    
    Expected event format:
    {
        "prompt": "Generate content...",
        "model_id": "mistral.mistral-7b-instruct-v0:2",  # optional
        "max_tokens": 2048,  # optional
        "temperature": 0.7,  # optional
        "character_context": "...",  # optional
        "world_rules": [...],  # optional
    }
    """
    try:
        # Extract parameters from event
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event
        
        prompt = body.get('prompt', '')
        model_id = body.get('model_id', os.environ.get('BEDROCK_MODEL_ID'))
        max_tokens = body.get('max_tokens', int(os.environ.get('MAX_TOKENS', 2048)))
        temperature = body.get('temperature', float(os.environ.get('TEMPERATURE', 0.7)))
        
        # Build enhanced prompt with context
        enhanced_prompt = build_enhanced_prompt(
            base_prompt=prompt,
            character_context=body.get('character_context'),
            world_rules=body.get('world_rules')
        )
        
        # Prepare request body for Mistral
        request_body = {
            "prompt": enhanced_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "top_k": 50
        }
        
        # Invoke Bedrock model
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        generated_text = response_body.get('outputs', [{}])[0].get('text', '')
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'generated_text': generated_text,
                'model_id': model_id,
                'tokens_used': response_body.get('outputs', [{}])[0].get('token_count', 0)
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

def build_enhanced_prompt(base_prompt: str, character_context: str = None, world_rules: list = None) -> str:
    """Build enhanced prompt with character context and world rules"""
    sections = []
    
    if character_context:
        sections.append(f"CHARACTER VOICE CONTEXT:\n{character_context}\n")
    
    if world_rules and len(world_rules) > 0:
        rules_text = "\n".join([
            f"- {rule['title']}: {rule['description']} (Category: {rule['category']})"
            for rule in world_rules
        ])
        sections.append(f"WORLD RULES TO FOLLOW:\n{rules_text}\n")
    
    sections.append(f"WRITING TASK:\n{base_prompt}")
    
    return "\n".join(sections)
```

### 1.7 Create New API Gateway

**Step 1: Create REST API**

```bash
# Create API
aws apigateway create-rest-api \
  --name ConsciousnessTrilogyAPI \
  --description "API for Consciousness Trilogy content generation" \
  --region ca-central-1 \
  --endpoint-configuration types=REGIONAL

# Save the API ID from output
API_ID=<your-api-id>

# Get root resource ID
aws apigateway get-resources \
  --rest-api-id $API_ID \
  --region ca-central-1
```

**Step 2: Create Resource and Method**

```bash
# Create /generate resource
aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id <ROOT_RESOURCE_ID> \
  --path-part generate \
  --region ca-central-1

RESOURCE_ID=<your-resource-id>

# Create POST method
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --authorization-type NONE \
  --region ca-central-1

# Create Lambda integration
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri arn:aws:apigateway:ca-central-1:lambda:path/2015-03-31/functions/arn:aws:lambda:ca-central-1:<ACCOUNT_ID>:function:ConsciousnessTrilogyBedrockAPI/invocations \
  --region ca-central-1
```

**Step 3: Grant API Gateway Permission to Invoke Lambda**

```bash
aws lambda add-permission \
  --function-name ConsciousnessTrilogyBedrockAPI \
  --statement-id apigateway-invoke-permission \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:ca-central-1:<ACCOUNT_ID>:${API_ID}/*/*" \
  --region ca-central-1
```

**Step 4: Deploy API**

```bash
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region ca-central-1
```

**Your API Endpoint:**
```
https://${API_ID}.execute-api.ca-central-1.amazonaws.com/prod/generate
```

**Alternative: Use AWS Console for API Gateway**

1. Navigate to API Gateway Console
2. Click "Create API" → REST API → Build
3. API name: `ConsciousnessTrilogyAPI`
4. Create Resource: `/generate`
5. Create Method: POST
6. Integration type: Lambda Function
7. Lambda Function: `ConsciousnessTrilogyBedrockAPI`
8. Deploy API to stage: `prod`

### 1.8 Test Your AWS Setup

```bash
# Test Lambda directly
aws lambda invoke \
  --function-name ConsciousnessTrilogyBedrockAPI \
  --payload '{"prompt":"Write a short paragraph about Mars colonization.","max_tokens":200}' \
  --region ca-central-1 \
  response.json

cat response.json

# Test via API Gateway
curl -X POST \
  https://${API_ID}.execute-api.ca-central-1.amazonaws.com/prod/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a short paragraph about Mars colonization.",
    "max_tokens": 200,
    "temperature": 0.7
  }'
```

---

## 2. Sentence Transformer Setup

### 2.1 Installation

```bash
# In your FastAPI project directory
pip install sentence-transformers==2.2.2
pip install chromadb==0.4.18

# Or add to requirements.txt
echo "sentence-transformers==2.2.2" >> requirements.txt
echo "chromadb==0.4.18" >> requirements.txt
pip install -r requirements.txt
```

### 2.2 Model Download and Initialization

**Create embedding service module:**

```python
# app/services/embedding_service.py
from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np
import os

class EmbeddingService:
    """
    Singleton service for generating embeddings using all-MiniLM-L6-v2
    
    Model specs:
    - Size: ~80MB
    - Embedding dimension: 384
    - Memory usage: ~500MB when loaded
    - Speed: ~1000 sentences/second on CPU
    """
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            self._load_model()
    
    def _load_model(self):
        """Load the embedding model (happens once on first call)"""
        print("Loading embedding model: all-MiniLM-L6-v2...")
        
        # Model will be downloaded to ~/.cache/torch/sentence_transformers/
        self._model = SentenceTransformer('all-MiniLM-L6-v2')
        
        print(f"Model loaded successfully. Embedding dimension: {self._model.get_sentence_embedding_dimension()}")
    
    def embed_text(self, text: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Generate embeddings for text
        
        Args:
            text: Single string or list of strings
            
        Returns:
            numpy array(s) of embeddings (dimension 384)
        """
        if isinstance(text, str):
            return self._model.encode(text, convert_to_numpy=True)
        else:
            return self._model.encode(text, convert_to_numpy=True)
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """
        Generate embeddings for a batch of texts efficiently
        
        Args:
            texts: List of strings to embed
            batch_size: Batch size for processing (default 32)
            
        Returns:
            List of numpy arrays (each dimension 384)
        """
        return self._model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100
        )
    
    def get_embedding_dimension(self) -> int:
        """Returns the embedding dimension (384 for all-MiniLM-L6-v2)"""
        return self._model.get_sentence_embedding_dimension()

# Global instance
embedding_service = EmbeddingService()
```

### 2.3 ChromaDB Client Configuration

```python
# app/services/chromadb_client.py
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import os

class ChromaDBClient:
    """
    Client for managing ChromaDB vector stores for Consciousness Trilogy app
    """
    
    def __init__(self):
        # Use persistent storage on external SSD
        persist_directory = os.getenv('CHROMADB_PERSIST_DIR', '/Volumes/ExternalSSD/consciousness_trilogy/chromadb')
        
        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        print(f"ChromaDB initialized with persist directory: {persist_directory}")
    
    def get_or_create_collection(
        self,
        collection_name: str,
        metadata: Optional[Dict] = None
    ):
        """
        Get existing collection or create new one
        
        Args:
            collection_name: Name of the collection
            metadata: Optional metadata for the collection
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            print(f"Retrieved existing collection: {collection_name}")
            return collection
        except:
            collection = self.client.create_collection(
                name=collection_name,
                metadata=metadata or {}
            )
            print(f"Created new collection: {collection_name}")
            return collection
    
    def delete_collection(self, collection_name: str):
        """Delete a collection"""
        try:
            self.client.delete_collection(name=collection_name)
            print(f"Deleted collection: {collection_name}")
        except Exception as e:
            print(f"Error deleting collection {collection_name}: {e}")
    
    def list_collections(self) -> List[str]:
        """List all collections"""
        collections = self.client.list_collections()
        return [c.name for c in collections]
    
    def persist(self):
        """Persist changes to disk"""
        self.client.persist()

# Global instance
chromadb_client = ChromaDBClient()
```

### 2.4 Environment Configuration

```bash
# Add to .env file
CHROMADB_PERSIST_DIR=/Volumes/ExternalSSD/consciousness_trilogy/chromadb
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
```

### 2.5 Memory Usage Verification

```python
# test_memory_usage.py
import psutil
import os
from app.services.embedding_service import embedding_service

def get_memory_usage():
    """Get current memory usage of the process"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

# Before loading model
memory_before = get_memory_usage()
print(f"Memory before loading model: {memory_before:.2f} MB")

# Load model and generate embedding
test_text = "This is a test sentence for embedding generation."
embedding = embedding_service.embed_text(test_text)

# After loading model
memory_after = get_memory_usage()
print(f"Memory after loading model: {memory_after:.2f} MB")
print(f"Memory used by model: {memory_after - memory_before:.2f} MB")
print(f"Embedding dimension: {len(embedding)}")
print(f"Embedding sample: {embedding[:5]}")
```

Expected output:
```
Loading embedding model: all-MiniLM-L6-v2...
Model loaded successfully. Embedding dimension: 384
Memory before loading model: 120.45 MB
Memory after loading model: 598.23 MB
Memory used by model: 477.78 MB
Embedding dimension: 384
```

---

## 3. Epic 5A Integration (Character RAG)

### 3.1 Character Embedding Service

```python
# app/services/character_embedding_service.py
from app.services.embedding_service import embedding_service
from app.services.chromadb_client import chromadb_client
from typing import List, Dict, Optional
import uuid
import json

class CharacterEmbeddingService:
    """
    Service for managing character-specific vector stores
    Each character gets its own ChromaDB collection
    """
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.chromadb_client = chromadb_client
    
    def get_collection_name(self, trilogy_id: str, character_id: str) -> str:
        """Generate collection name for a character"""
        return f"{trilogy_id}_character_{character_id}"
    
    async def initialize_character_vector_store(
        self,
        trilogy_id: str,
        character_id: str,
        character_data: Dict
    ) -> Dict:
        """
        Initialize vector store for a new character
        
        Args:
            trilogy_id: ID of the trilogy project
            character_id: ID of the character
            character_data: Dict containing name, description, traits, arc, themes
            
        Returns:
            Dict with collection info and status
        """
        collection_name = self.get_collection_name(trilogy_id, character_id)
        
        # Create collection with metadata
        collection = self.chromadb_client.get_or_create_collection(
            collection_name=collection_name,
            metadata={
                "trilogy_id": trilogy_id,
                "character_id": character_id,
                "character_name": character_data.get('name'),
                "type": "character_context"
            }
        )
        
        # Prepare documents to embed
        documents = self._prepare_character_documents(character_data)
        
        # Generate embeddings
        embeddings = self.embedding_service.embed_batch([doc['text'] for doc in documents])
        
        # Add to collection
        collection.add(
            ids=[doc['id'] for doc in documents],
            embeddings=embeddings.tolist(),
            documents=[doc['text'] for doc in documents],
            metadatas=[doc['metadata'] for doc in documents]
        )
        
        # Persist to disk
        self.chromadb_client.persist()
        
        return {
            "collection_name": collection_name,
            "document_count": len(documents),
            "character_id": character_id,
            "status": "completed"
        }
    
    def _prepare_character_documents(self, character_data: Dict) -> List[Dict]:
        """
        Prepare character data for embedding
        
        Creates separate documents for:
        - Character profile
        - Character traits
        - Character arc
        - Consciousness themes
        """
        character_id = character_data.get('id')
        documents = []
        
        # Character profile
        if character_data.get('description'):
            documents.append({
                'id': f"{character_id}_profile",
                'text': f"Character Profile: {character_data['name']}\n{character_data['description']}",
                'metadata': {
                    'character_id': character_id,
                    'document_type': 'profile',
                    'character_name': character_data['name']
                }
            })
        
        # Character traits
        if character_data.get('traits'):
            traits_text = json.dumps(character_data['traits'], indent=2)
            documents.append({
                'id': f"{character_id}_traits",
                'text': f"Character Traits: {character_data['name']}\n{traits_text}",
                'metadata': {
                    'character_id': character_id,
                    'document_type': 'traits',
                    'character_name': character_data['name']
                }
            })
        
        # Character arc
        if character_data.get('character_arc'):
            documents.append({
                'id': f"{character_id}_arc",
                'text': f"Character Arc: {character_data['name']}\n{character_data['character_arc']}",
                'metadata': {
                    'character_id': character_id,
                    'document_type': 'arc',
                    'character_name': character_data['name']
                }
            })
        
        # Consciousness themes
        if character_data.get('consciousness_themes'):
            themes_text = ', '.join(character_data['consciousness_themes'])
            documents.append({
                'id': f"{character_id}_themes",
                'text': f"Consciousness Themes: {character_data['name']}\n{themes_text}",
                'metadata': {
                    'character_id': character_id,
                    'document_type': 'consciousness_themes',
                    'character_name': character_data['name']
                }
            })
        
        return documents
    
    async def query_character_context(
        self,
        trilogy_id: str,
        character_id: str,
        query_text: str,
        n_results: int = 5
    ) -> List[Dict]:
        """
        Query character-specific context for content generation
        
        Args:
            trilogy_id: ID of the trilogy project
            character_id: ID of the character
            query_text: Text to find similar context for (e.g., writing prompt)
            n_results: Number of results to return
            
        Returns:
            List of relevant character context documents
        """
        collection_name = self.get_collection_name(trilogy_id, character_id)
        
        try:
            collection = self.chromadb_client.client.get_collection(collection_name)
        except:
            print(f"Collection not found: {collection_name}")
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query_text)
        
        # Query collection
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'similarity': 1 - results['distances'][0][i]  # Convert distance to similarity
            })
        
        return formatted_results
    
    async def add_character_context(
        self,
        trilogy_id: str,
        character_id: str,
        content: str,
        metadata: Dict
    ):
        """
        Add new context to character's vector store after content generation
        
        Args:
            trilogy_id: ID of the trilogy project
            character_id: ID of the character
            content: Generated content to add as context
            metadata: Additional metadata (chapter, book, etc.)
        """
        collection_name = self.get_collection_name(trilogy_id, character_id)
        collection = self.chromadb_client.client.get_collection(collection_name)
        
        # Generate embedding
        embedding = self.embedding_service.embed_text(content)
        
        # Generate unique ID
        doc_id = f"{character_id}_{uuid.uuid4()}"
        
        # Add to collection
        collection.add(
            ids=[doc_id],
            embeddings=[embedding.tolist()],
            documents=[content],
            metadatas=[{
                'character_id': character_id,
                'document_type': 'generated_content',
                **metadata
            }]
        )
        
        # Persist
        self.chromadb_client.persist()

# Global instance
character_embedding_service = CharacterEmbeddingService()
```

### 3.2 Character RAG Generator

```python
# app/services/character_rag_generator.py
from app.services.character_embedding_service import character_embedding_service
from typing import Dict, List, Optional
import httpx
import os

class CharacterRAGGenerator:
    """
    Core service for generating character-consistent content using RAG
    """
    
    def __init__(self):
        self.character_service = character_embedding_service
        self.bedrock_api_url = os.getenv(
            'BEDROCK_API_URL',
            'https://YOUR_API_ID.execute-api.ca-central-1.amazonaws.com/prod/generate'
        )
    
    async def generate_content(
        self,
        trilogy_id: str,
        character_id: str,
        sub_chapter_id: str,
        prompt: str,
        plot_points: str,
        target_word_count: int = 2000
    ) -> Dict:
        """
        Generate character-consistent content using RAG
        
        Args:
            trilogy_id: ID of the trilogy project
            character_id: ID of the character narrating this sub-chapter
            sub_chapter_id: ID of the sub-chapter
            prompt: Writing prompt from author
            plot_points: Plot points to cover
            target_word_count: Target word count for generation
            
        Returns:
            Dict with generated content and metadata
        """
        # Step 1: Retrieve character context via RAG
        query_text = f"{prompt}\n{plot_points}"
        character_context = await self.character_service.query_character_context(
            trilogy_id=trilogy_id,
            character_id=character_id,
            query_text=query_text,
            n_results=5
        )
        
        # Step 2: Build enhanced prompt
        enhanced_prompt = self._build_character_prompt(
            character_context=character_context,
            prompt=prompt,
            plot_points=plot_points,
            target_word_count=target_word_count
        )
        
        # Step 3: Call Bedrock API
        generated_content = await self._call_bedrock_api(
            prompt=enhanced_prompt,
            max_tokens=target_word_count * 2  # Rough token estimate
        )
        
        # Step 4: Store generated content as new character context
        await self.character_service.add_character_context(
            trilogy_id=trilogy_id,
            character_id=character_id,
            content=generated_content,
            metadata={
                'sub_chapter_id': sub_chapter_id,
                'generation_type': 'sub_chapter_content'
            }
        )
        
        return {
            'generated_content': generated_content,
            'character_id': character_id,
            'sub_chapter_id': sub_chapter_id,
            'context_used': len(character_context)
        }
    
    def _build_character_prompt(
        self,
        character_context: List[Dict],
        prompt: str,
        plot_points: str,
        target_word_count: int
    ) -> str:
        """Build enhanced prompt with character context"""
        
        # Format character context
        context_text = "\n\n".join([
            f"{ctx['metadata']['document_type'].upper()}:\n{ctx['text']}"
            for ctx in character_context
        ])
        
        enhanced_prompt = f"""You are writing from the perspective of this character. Use the character context below to maintain voice consistency.

{context_text}

WRITING TASK:
{prompt}

PLOT POINTS TO COVER:
{plot_points}

TARGET LENGTH: Approximately {target_word_count} words

Write the content maintaining the character's voice, personality, and consciousness themes as described above. The content should feel authentic to this character's perspective."""
        
        return enhanced_prompt
    
    async def _call_bedrock_api(self, prompt: str, max_tokens: int) -> str:
        """Call AWS Bedrock API via API Gateway"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                self.bedrock_api_url,
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Bedrock API error: {response.text}")
            
            result = response.json()
            return result['generated_text']

# Global instance
character_rag_generator = CharacterRAGGenerator()
```

### 3.3 FastAPI Endpoints for Epic 5A

```python
# app/api/characters.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, List
from app.services.character_embedding_service import character_embedding_service
from app.services.character_rag_generator import character_rag_generator

router = APIRouter(prefix="/api/characters", tags=["characters"])

class CharacterCreate(BaseModel):
    trilogy_id: str
    name: str
    description: Optional[str] = None
    traits: Optional[Dict] = None
    consciousness_themes: Optional[List[str]] = None
    character_arc: Optional[str] = None

class GenerateContentRequest(BaseModel):
    trilogy_id: str
    character_id: str
    sub_chapter_id: str
    prompt: str
    plot_points: str
    target_word_count: int = 2000

@router.post("/initialize-vector-store")
async def initialize_character_vector_store(
    character: CharacterCreate,
    background_tasks: BackgroundTasks
):
    """
    Initialize vector store for a new character
    Runs embedding in background
    """
    try:
        # Queue background task
        background_tasks.add_task(
            character_embedding_service.initialize_character_vector_store,
            trilogy_id=character.trilogy_id,
            character_id=character.dict().get('id', 'temp_id'),
            character_data=character.dict()
        )
        
        return {
            "status": "queued",
            "message": "Character embedding job queued"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-content")
async def generate_character_content(request: GenerateContentRequest):
    """
    Generate content using Character RAG
    """
    try:
        result = await character_rag_generator.generate_content(
            trilogy_id=request.trilogy_id,
            character_id=request.character_id,
            sub_chapter_id=request.sub_chapter_id,
            prompt=request.prompt,
            plot_points=request.plot_points,
            target_word_count=request.target_word_count
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/context/{trilogy_id}/{character_id}")
async def query_character_context(
    trilogy_id: str,
    character_id: str,
    query: str,
    n_results: int = 5
):
    """
    Query character context for preview
    """
    try:
        results = await character_embedding_service.query_character_context(
            trilogy_id=trilogy_id,
            character_id=character_id,
            query_text=query,
            n_results=n_results
        )
        
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 4. Epic 5B Integration (World Rule RAG)

### 4.1 World Rule Embedding Service

```python
# app/services/world_rule_embedding_service.py
from app.services.embedding_service import embedding_service
from app.services.chromadb_client import chromadb_client
from typing import List, Dict, Optional
import uuid

class WorldRuleEmbeddingService:
    """
    Service for managing world rule vector stores
    All rules for a trilogy share one collection
    """
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.chromadb_client = chromadb_client
    
    def get_collection_name(self, trilogy_id: str) -> str:
        """Generate collection name for world rules"""
        return f"{trilogy_id}_world_rules"
    
    async def initialize_world_rules_collection(self, trilogy_id: str) -> Dict:
        """
        Initialize vector store for world rules
        Called once per trilogy
        """
        collection_name = self.get_collection_name(trilogy_id)
        
        collection = self.chromadb_client.get_or_create_collection(
            collection_name=collection_name,
            metadata={
                "trilogy_id": trilogy_id,
                "type": "world_rules"
            }
        )
        
        return {
            "collection_name": collection_name,
            "status": "initialized"
        }
    
    async def embed_world_rule(
        self,
        trilogy_id: str,
        rule_id: str,
        rule_data: Dict
    ) -> Dict:
        """
        Embed a single world rule
        
        Args:
            trilogy_id: ID of the trilogy
            rule_id: ID of the world rule
            rule_data: Dict containing title, description, category, book_ids
            
        Returns:
            Dict with embedding status
        """
        collection_name = self.get_collection_name(trilogy_id)
        collection = self.chromadb_client.client.get_collection(collection_name)
        
        # Prepare text for embedding
        embedding_text = self._prepare_rule_text(rule_data)
        
        # Generate embedding
        embedding = self.embedding_service.embed_text(embedding_text)
        
        # Add to collection
        collection.add(
            ids=[rule_id],
            embeddings=[embedding.tolist()],
            documents=[embedding_text],
            metadatas=[{
                'trilogy_id': trilogy_id,
                'rule_id': rule_id,
                'category': rule_data.get('category', 'general'),
                'book_ids': rule_data.get('book_ids', []),
                'accuracy': rule_data.get('accuracy', 1.0)
            }]
        )
        
        # Persist
        self.chromadb_client.persist()
        
        return {
            "rule_id": rule_id,
            "collection_name": collection_name,
            "status": "completed"
        }
    
    def _prepare_rule_text(self, rule_data: Dict) -> str:
        """
        Prepare world rule text for embedding
        Combines title, description, and category
        """
        parts = []
        
        if rule_data.get('title'):
            parts.append(f"Title: {rule_data['title']}")
        
        if rule_data.get('description'):
            parts.append(f"Description: {rule_data['description']}")
        
        if rule_data.get('category'):
            parts.append(f"Category: {rule_data['category']}")
        
        return "\n".join(parts)
    
    async def query_relevant_rules(
        self,
        trilogy_id: str,
        book_id: int,
        query_text: str,
        max_rules: int = 10,
        similarity_threshold: float = 0.65
    ) -> List[Dict]:
        """
        Query relevant world rules for content generation
        
        Args:
            trilogy_id: ID of the trilogy
            book_id: Book number (1, 2, or 3) for filtering
            query_text: Text to find relevant rules for (prompt + plot points)
            max_rules: Maximum number of rules to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of relevant world rules with similarity scores
        """
        collection_name = self.get_collection_name(trilogy_id)
        
        try:
            collection = self.chromadb_client.client.get_collection(collection_name)
        except:
            print(f"Collection not found: {collection_name}")
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query_text)
        
        # Query collection (request 2x max_rules for filtering)
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=max_rules * 2,
            where={"trilogy_id": trilogy_id}  # Basic filter
        )
        
        # Format and filter results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            similarity = 1 - results['distances'][0][i]
            metadata = results['metadatas'][0][i]
            
            # Filter by book association
            book_ids = metadata.get('book_ids', [])
            if book_id not in book_ids:
                continue
            
            # Filter by similarity threshold
            if similarity < similarity_threshold:
                continue
            
            # Apply accuracy weighting
            accuracy = metadata.get('accuracy', 1.0)
            adjusted_similarity = similarity * (0.7 if accuracy < 0.5 else 1.0)
            
            formatted_results.append({
                'rule_id': metadata['rule_id'],
                'text': results['documents'][0][i],
                'category': metadata['category'],
                'similarity': similarity,
                'adjusted_similarity': adjusted_similarity,
                'accuracy': accuracy
            })
        
        # Sort by adjusted similarity and take top N
        formatted_results.sort(key=lambda x: x['adjusted_similarity'], reverse=True)
        return formatted_results[:max_rules]

# Global instance
world_rule_embedding_service = WorldRuleEmbeddingService()
```

### 4.2 World Rule RAG Provider

```python
# app/services/world_rule_rag_provider.py
from app.services.world_rule_embedding_service import world_rule_embedding_service
from typing import List, Dict, Optional
import hashlib
import json

class WorldRuleRAGProvider:
    """
    Service for providing world rule context during content generation
    Integrates with Character RAG (Epic 5A)
    """
    
    def __init__(self):
        self.rule_service = world_rule_embedding_service
        # Redis cache would be initialized here
        self.cache = None  # TODO: Implement Redis caching
    
    async def get_rules_for_generation(
        self,
        trilogy_id: str,
        book_id: int,
        prompt: str,
        plot_points: str,
        max_rules: int = 10,
        similarity_threshold: float = 0.65
    ) -> List[Dict]:
        """
        Get relevant world rules for content generation
        
        This method:
        1. Checks cache first (if available)
        2. Queries ChromaDB for semantically similar rules
        3. Filters by book association
        4. Applies accuracy weighting
        5. Caches results
        
        Args:
            trilogy_id: ID of the trilogy
            book_id: Book number for filtering
            prompt: Writing prompt
            plot_points: Plot points to cover
            max_rules: Maximum rules to return
            similarity_threshold: Minimum similarity
            
        Returns:
            List of relevant world rules
        """
        # Build query text
        query_text = f"{prompt}\n{plot_points}"
        
        # Check cache (if implemented)
        cache_key = self._get_cache_key(book_id, query_text)
        # cached_rules = await self._get_from_cache(cache_key)
        # if cached_rules:
        #     return cached_rules
        
        # Query ChromaDB
        rules = await self.rule_service.query_relevant_rules(
            trilogy_id=trilogy_id,
            book_id=book_id,
            query_text=query_text,
            max_rules=max_rules,
            similarity_threshold=similarity_threshold
        )
        
        # Cache results (if implemented)
        # await self._set_in_cache(cache_key, rules, ttl=900)  # 15 minutes
        
        return rules
    
    def _get_cache_key(self, book_id: int, query_text: str) -> str:
        """Generate cache key for rule query"""
        query_hash = hashlib.md5(query_text.encode()).hexdigest()
        return f"rules:{book_id}:{query_hash}"
    
    def format_rules_for_prompt(self, rules: List[Dict]) -> str:
        """
        Format rules for inclusion in LLM prompt
        
        Returns formatted string ready to include in prompt
        """
        if not rules:
            return ""
        
        formatted = ["WORLD RULES TO FOLLOW:"]
        for i, rule in enumerate(rules, 1):
            # Parse rule text (it's in "Title: X\nDescription: Y\nCategory: Z" format)
            lines = rule['text'].split('\n')
            title = lines[0].replace('Title: ', '') if len(lines) > 0 else 'Unknown'
            description = lines[1].replace('Description: ', '') if len(lines) > 1 else ''
            category = rule['category']
            
            formatted.append(
                f"\n{i}. {title} (Category: {category})\n   {description}"
            )
        
        return "\n".join(formatted)

# Global instance
world_rule_rag_provider = WorldRuleRAGProvider()
```

### 4.3 Combined Generation with Character + World Rule RAG

```python
# app/services/combined_rag_generator.py
from app.services.character_rag_generator import character_rag_generator
from app.services.world_rule_rag_provider import world_rule_rag_provider
from typing import Dict
import asyncio

class CombinedRAGGenerator:
    """
    Generates content using both Character RAG (Epic 5A) and World Rule RAG (Epic 5B)
    """
    
    def __init__(self):
        self.character_generator = character_rag_generator
        self.world_rule_provider = world_rule_rag_provider
    
    async def generate_content(
        self,
        trilogy_id: str,
        book_id: int,
        character_id: str,
        sub_chapter_id: str,
        prompt: str,
        plot_points: str,
        target_word_count: int = 2000
    ) -> Dict:
        """
        Generate content using parallel retrieval of:
        1. Character context (Epic 5A)
        2. World rule context (Epic 5B)
        3. Previous content context (future)
        
        All three retrievals happen simultaneously to minimize latency
        """
        # PARALLEL RETRIEVAL - All three happen simultaneously
        query_text = f"{prompt}\n{plot_points}"
        
        character_context_task = self.character_generator.character_service.query_character_context(
            trilogy_id=trilogy_id,
            character_id=character_id,
            query_text=query_text,
            n_results=5
        )
        
        world_rules_task = self.world_rule_provider.get_rules_for_generation(
            trilogy_id=trilogy_id,
            book_id=book_id,
            prompt=prompt,
            plot_points=plot_points,
            max_rules=10
        )
        
        # Wait for both to complete
        character_context, world_rules = await asyncio.gather(
            character_context_task,
            world_rules_task
        )
        
        # Build comprehensive prompt
        enhanced_prompt = self._build_comprehensive_prompt(
            character_context=character_context,
            world_rules=world_rules,
            prompt=prompt,
            plot_points=plot_points,
            target_word_count=target_word_count
        )
        
        # Generate content
        generated_content = await self.character_generator._call_bedrock_api(
            prompt=enhanced_prompt,
            max_tokens=target_word_count * 2
        )
        
        # Update character context
        await self.character_generator.character_service.add_character_context(
            trilogy_id=trilogy_id,
            character_id=character_id,
            content=generated_content,
            metadata={
                'sub_chapter_id': sub_chapter_id,
                'generation_type': 'sub_chapter_content',
                'rules_used': len(world_rules)
            }
        )
        
        return {
            'generated_content': generated_content,
            'character_id': character_id,
            'sub_chapter_id': sub_chapter_id,
            'context_used': len(character_context),
            'rules_used': len(world_rules),
            'world_rules': [r['rule_id'] for r in world_rules]
        }
    
    def _build_comprehensive_prompt(
        self,
        character_context: list,
        world_rules: list,
        prompt: str,
        plot_points: str,
        target_word_count: int
    ) -> str:
        """Build comprehensive prompt with both character and world rule context"""
        
        sections = []
        
        # Character voice section
        if character_context:
            context_text = "\n\n".join([
                f"{ctx['metadata']['document_type'].upper()}:\n{ctx['text']}"
                for ctx in character_context
            ])
            sections.append(f"CHARACTER VOICE CONTEXT:\n{context_text}")
        
        # World rules section
        if world_rules:
            rules_text = self.world_rule_provider.format_rules_for_prompt(world_rules)
            sections.append(rules_text)
        
        # Writing task
        sections.append(f"""WRITING TASK:
{prompt}

PLOT POINTS TO COVER:
{plot_points}

TARGET LENGTH: Approximately {target_word_count} words

Write the content maintaining the character's voice while respecting the world rules above. The content should feel authentic to this character's perspective and consistent with the established universe constraints.""")
        
        return "\n\n".join(sections)

# Global instance
combined_rag_generator = CombinedRAGGenerator()
```

### 4.4 FastAPI Endpoints for Combined RAG

```python
# app/api/generation.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.combined_rag_generator import combined_rag_generator

router = APIRouter(prefix="/api/generation", tags=["generation"])

class CombinedGenerateRequest(BaseModel):
    trilogy_id: str
    book_id: int
    character_id: str
    sub_chapter_id: str
    prompt: str
    plot_points: str
    target_word_count: int = 2000

@router.post("/combined-rag")
async def generate_with_combined_rag(request: CombinedGenerateRequest):
    """
    Generate content using both Character RAG (Epic 5A) and World Rule RAG (Epic 5B)
    """
    try:
        result = await combined_rag_generator.generate_content(
            trilogy_id=request.trilogy_id,
            book_id=request.book_id,
            character_id=request.character_id,
            sub_chapter_id=request.sub_chapter_id,
            prompt=request.prompt,
            plot_points=request.plot_points,
            target_word_count=request.target_word_count
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 5. Testing & Validation

### 5.1 Test AWS Setup

```bash
# Test Lambda function
python test_aws_lambda.py
```

```python
# test_aws_lambda.py
import boto3
import json

# Initialize Lambda client
lambda_client = boto3.client('lambda', region_name='ca-central-1')

# Test payload
payload = {
    "prompt": "Write a paragraph about Mars colonization from a character who fears losing their humanity.",
    "max_tokens": 200,
    "temperature": 0.7
}

# Invoke function
response = lambda_client.invoke(
    FunctionName='ConsciousnessTrilogyBedrockAPI',
    InvocationType='RequestResponse',
    Payload=json.dumps(payload)
)

# Parse response
result = json.loads(response['Payload'].read())
print(json.dumps(result, indent=2))
```

### 5.2 Test Embedding Service

```python
# test_embedding_service.py
from app.services.embedding_service import embedding_service

# Test single text
text = "This is a test sentence for embedding."
embedding = embedding_service.embed_text(text)
print(f"Embedding dimension: {len(embedding)}")
print(f"First 5 values: {embedding[:5]}")

# Test batch
texts = [
    "Mars colonization requires radiation shielding.",
    "The character struggles with AI consciousness.",
    "Terraforming takes centuries of careful planning."
]
embeddings = embedding_service.embed_batch(texts)
print(f"Batch size: {len(embeddings)}")
print(f"Each embedding dimension: {len(embeddings[0])}")
```

### 5.3 Test Character RAG (Epic 5A)

```python
# test_character_rag.py
import asyncio
from app.services.character_embedding_service import character_embedding_service

async def test_character_rag():
    # Test data
    trilogy_id = "test_trilogy_001"
    character_id = "test_character_001"
    character_data = {
        "id": character_id,
        "name": "Dr. Sarah Chen",
        "description": "A brilliant neuroscientist who questions the nature of consciousness after her AI research leads to unexpected breakthroughs.",
        "traits": {
            "analytical": "high",
            "empathetic": "medium",
            "risk_taking": "low"
        },
        "character_arc": "Begins as skeptical materialist, evolves to accept consciousness may transcend physical substrate.",
        "consciousness_themes": [
            "mind-body problem",
            "emergence",
            "personal identity"
        ]
    }
    
    # Initialize vector store
    print("Initializing character vector store...")
    result = await character_embedding_service.initialize_character_vector_store(
        trilogy_id=trilogy_id,
        character_id=character_id,
        character_data=character_data
    )
    print(f"Initialization result: {result}")
    
    # Query character context
    print("\nQuerying character context...")
    query = "Write about the ethical implications of consciousness transfer"
    context = await character_embedding_service.query_character_context(
        trilogy_id=trilogy_id,
        character_id=character_id,
        query_text=query,
        n_results=3
    )
    
    print(f"Retrieved {len(context)} context documents:")
    for i, ctx in enumerate(context, 1):
        print(f"\n{i}. Type: {ctx['metadata']['document_type']}")
        print(f"   Similarity: {ctx['similarity']:.3f}")
        print(f"   Text preview: {ctx['text'][:100]}...")

if __name__ == "__main__":
    asyncio.run(test_character_rag())
```

### 5.4 Test World Rule RAG (Epic 5B)

```python
# test_world_rule_rag.py
import asyncio
from app.services.world_rule_embedding_service import world_rule_embedding_service

async def test_world_rule_rag():
    # Test data
    trilogy_id = "test_trilogy_001"
    
    # Initialize collection
    print("Initializing world rules collection...")
    result = await world_rule_embedding_service.initialize_world_rules_collection(trilogy_id)
    print(f"Initialization result: {result}")
    
    # Add test rules
    test_rules = [
        {
            "id": "rule_001",
            "title": "Consciousness Transfer Limitation",
            "description": "Consciousness can only be transferred if the neural pathways are mapped at quantum precision. Any loss of precision >0.1% results in personality degradation.",
            "category": "consciousness_mechanics",
            "book_ids": [1, 2, 3],
            "accuracy": 0.95
        },
        {
            "id": "rule_002",
            "title": "Mars Atmospheric Pressure",
            "description": "Mars atmospheric pressure is 0.6% of Earth's. Permanent habitats must maintain 1 atm pressure with redundant systems.",
            "category": "environment",
            "book_ids": [1, 2, 3],
            "accuracy": 1.0
        },
        {
            "id": "rule_003",
            "title": "AI Rights Timeline",
            "description": "AI gained legal personhood rights in 2087 after the Singapore Accord. Before this, AIs had no legal standing.",
            "category": "society",
            "book_ids": [2, 3],
            "accuracy": 0.90
        }
    ]
    
    print("\nEmbedding test rules...")
    for rule in test_rules:
        result = await world_rule_embedding_service.embed_world_rule(
            trilogy_id=trilogy_id,
            rule_id=rule["id"],
            rule_data=rule
        )
        print(f"Embedded rule: {rule['title']}")
    
    # Query relevant rules
    print("\nQuerying relevant rules...")
    query_prompt = "Write about transferring consciousness to an AI system"
    query_plot = "The character must decide whether to upload their mind before their body fails"
    
    rules = await world_rule_embedding_service.query_relevant_rules(
        trilogy_id=trilogy_id,
        book_id=1,
        query_text=f"{query_prompt}\n{query_plot}",
        max_rules=10,
        similarity_threshold=0.5
    )
    
    print(f"\nRetrieved {len(rules)} relevant rules:")
    for i, rule in enumerate(rules, 1):
        print(f"\n{i}. Rule ID: {rule['rule_id']}")
        print(f"   Category: {rule['category']}")
        print(f"   Similarity: {rule['similarity']:.3f}")
        print(f"   Adjusted Similarity: {rule['adjusted_similarity']:.3f}")
        print(f"   Accuracy: {rule['accuracy']:.2f}")
        print(f"   Text preview: {rule['text'][:100]}...")

if __name__ == "__main__":
    asyncio.run(test_world_rule_rag())
```

### 5.5 End-to-End Test

```python
# test_end_to_end.py
import asyncio
from app.services.combined_rag_generator import combined_rag_generator

async def test_end_to_end():
    """Test complete generation flow with both Character and World Rule RAG"""
    
    request_data = {
        "trilogy_id": "test_trilogy_001",
        "book_id": 1,
        "character_id": "test_character_001",
        "sub_chapter_id": "sub_chapter_001",
        "prompt": "Write about the moment when the character must decide whether to transfer their consciousness to preserve their life, knowing the risks of personality degradation.",
        "plot_points": "- Character receives terminal diagnosis\n- AI offers consciousness transfer\n- Character wrestles with identity concerns\n- Decision must be made within 48 hours",
        "target_word_count": 500
    }
    
    print("Generating content with combined RAG...")
    print(f"Character: {request_data['character_id']}")
    print(f"Book: {request_data['book_id']}")
    print(f"Target: {request_data['target_word_count']} words\n")
    
    result = await combined_rag_generator.generate_content(**request_data)
    
    print("\n=== GENERATION RESULT ===")
    print(f"Context documents used: {result['context_used']}")
    print(f"World rules used: {result['rules_used']}")
    print(f"Rule IDs: {result['world_rules']}")
    print(f"\n=== GENERATED CONTENT ===")
    print(result['generated_content'])
    print(f"\n=== END ===")

if __name__ == "__main__":
    asyncio.run(test_end_to_end())
```

---

## 6. Troubleshooting

### 6.1 AWS Lambda Issues

**Issue: Lambda timeout**
```
Solution: Increase timeout in Lambda configuration
aws lambda update-function-configuration \
  --function-name ConsciousnessTrilogyBedrockAPI \
  --timeout 120
```

**Issue: Bedrock permissions denied**
```
Solution: Verify IAM role has correct Bedrock permissions
aws iam get-role-policy \
  --role-name ConsciousnessTrilogyLambdaRole \
  --policy-name BedrockAccessPolicy
```

**Issue: API Gateway 502 error**
```
Solution: Check Lambda logs
aws logs tail /aws/lambda/ConsciousnessTrilogyBedrockAPI --follow
```

### 6.2 Embedding Service Issues

**Issue: Model download fails**
```python
# Solution: Manually download model
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder='./models')
```

**Issue: Out of memory on 8GB MacBook**
```python
# Solution: Clear model cache periodically
import torch
torch.cuda.empty_cache()  # If using GPU
# Or restart FastAPI server periodically
```

**Issue: Slow embedding generation**
```python
# Solution: Use batch processing
texts = [...]  # Large list of texts
embeddings = embedding_service.embed_batch(texts, batch_size=32)
```

### 6.3 ChromaDB Issues

**Issue: Collection not found**
```python
# Solution: Initialize collection first
await character_embedding_service.initialize_character_vector_store(...)
```

**Issue: External SSD not mounted**
```bash
# Solution: Check mount point
ls -la /Volumes/ExternalSSD/
# Update CHROMADB_PERSIST_DIR in .env if needed
```

**Issue: Query returns no results**
```python
# Solution: Lower similarity threshold
results = await query_character_context(
    ...,
    n_results=10  # Increase n_results
)
# Or check if collection has documents
collection = chromadb_client.client.get_collection(collection_name)
print(f"Document count: {collection.count()}")
```

### 6.4 Integration Issues

**Issue: Character context not being used**
```python
# Solution: Verify collection exists and has documents
from app.services.chromadb_client import chromadb_client
collections = chromadb_client.list_collections()
print(f"Available collections: {collections}")
```

**Issue: World rules not relevant**
```python
# Solution: Adjust similarity threshold or max_rules
rules = await world_rule_rag_provider.get_rules_for_generation(
    ...,
    similarity_threshold=0.5,  # Lower threshold
    max_rules=15  # Increase max
)
```

**Issue: Generation quality poor**
```python
# Solution: Improve prompt engineering
# - Add more context documents
# - Provide better character descriptions
# - Add more world rules
# - Increase temperature for creativity
# - Adjust max_tokens for length
```

---

## Summary Checklist

### AWS Setup ✓
- [ ] IAM role created with Bedrock permissions
- [ ] Lambda function created and configured
- [ ] API Gateway created and deployed
- [ ] Tested Lambda invocation
- [ ] Tested API Gateway endpoint

### Sentence Transformer Setup ✓
- [ ] `sentence-transformers` installed
- [ ] `chromadb` installed
- [ ] Model downloads successfully (~80MB)
- [ ] Memory usage verified (<600MB)
- [ ] EmbeddingService created and tested

### Epic 5A (Character RAG) ✓
- [ ] CharacterEmbeddingService implemented
- [ ] Character vector stores initialize correctly
- [ ] Character context retrieval working
- [ ] CharacterRAGGenerator implemented
- [ ] API endpoints created and tested

### Epic 5B (World Rule RAG) ✓
- [ ] WorldRuleEmbeddingService implemented
- [ ] World rules collection initializes correctly
- [ ] Rule embedding working
- [ ] WorldRuleRAGProvider implemented
- [ ] Rule retrieval with filtering working

### Combined RAG ✓
- [ ] CombinedRAGGenerator implemented
- [ ] Parallel retrieval working
- [ ] Comprehensive prompts generated correctly
- [ ] API endpoint created and tested
- [ ] End-to-end test passes

---

## Next Steps

1. **Implement Redis caching** for world rule queries (15-minute TTL)
2. **Add WebSocket support** for real-time generation progress
3. **Implement pg-boss** for async job processing
4. **Add consistency checking** (Epic 7) to validate rule adherence
5. **Build Streamlit frontend** for user interaction
6. **Optimize performance** based on usage patterns
7. **Add monitoring and logging** for production deployment

---

**Document Version:** 1.0  
**Last Updated:** November 2, 2025  
**Author:** Technical Documentation for Consciousness Trilogy App
