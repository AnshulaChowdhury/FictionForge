# Quick Reference Guide: AWS + Embedding Setup
## Consciousness Trilogy App - Essential Commands & Code

---

## AWS Lambda Quick Setup

### 1. Create IAM Role (One-time)
```bash
# Create role
aws iam create-role \
  --role-name ConsciousnessTrilogyLambdaRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name ConsciousnessTrilogyLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Add Bedrock access
aws iam put-role-policy \
  --role-name ConsciousnessTrilogyLambdaRole \
  --policy-name BedrockAccessPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      "Resource": "arn:aws:bedrock:ca-central-1::foundation-model/mistral.*"
    }]
  }'
```

### 2. Export Existing Lambda
```bash
# Get function code
aws lambda get-function \
  --function-name FictionForgeLLM \
  --region ca-central-1 \
  --query 'Code.Location' --output text | xargs curl -o function.zip
```

### 3. Create New Lambda
```bash
# Via Console is easier for first time:
# 1. Lambda Console → Create function
# 2. Name: ConsciousnessTrilogyBedrockAPI
# 3. Runtime: Python 3.11
# 4. Role: ConsciousnessTrilogyLambdaRole
# 5. Upload function.zip
# 6. Set timeout: 60s, memory: 1024MB
```

### 4. Create API Gateway (Console)
```
1. API Gateway Console → Create API → REST API
2. Name: ConsciousnessTrilogyAPI
3. Create resource: /generate
4. Create method: POST
5. Integration: Lambda → ConsciousnessTrilogyBedrockAPI
6. Deploy to stage: prod
```

### 5. Test Your Setup
```bash
# Get your API endpoint (replace API_ID)
API_URL="https://YOUR_API_ID.execute-api.ca-central-1.amazonaws.com/prod/generate"

# Test
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write about Mars colonization",
    "max_tokens": 200,
    "temperature": 0.7
  }'
```

---

## Sentence Transformer Setup

### Installation
```bash
pip install sentence-transformers==2.2.2 chromadb==0.4.18
```

### Core Service
```python
# app/services/embedding_service.py
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            print("Loading all-MiniLM-L6-v2...")
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def embed_text(self, text):
        return self._model.encode(text, convert_to_numpy=True)
    
    def embed_batch(self, texts, batch_size=32):
        return self._model.encode(texts, batch_size=batch_size, convert_to_numpy=True)

embedding_service = EmbeddingService()
```

### ChromaDB Client
```python
# app/services/chromadb_client.py
import chromadb
from chromadb.config import Settings
import os

class ChromaDBClient:
    def __init__(self):
        persist_dir = os.getenv('CHROMADB_PERSIST_DIR', '/Volumes/ExternalSSD/consciousness_trilogy/chromadb')
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_dir,
            anonymized_telemetry=False
        ))
    
    def get_or_create_collection(self, collection_name, metadata=None):
        try:
            return self.client.get_collection(name=collection_name)
        except:
            return self.client.create_collection(name=collection_name, metadata=metadata or {})
    
    def persist(self):
        self.client.persist()

chromadb_client = ChromaDBClient()
```

---

## Epic 5A: Character RAG

### Character Embedding
```python
# Initialize character vector store
from app.services.embedding_service import embedding_service
from app.services.chromadb_client import chromadb_client

def initialize_character(trilogy_id, character_id, character_data):
    # Create collection
    collection_name = f"{trilogy_id}_character_{character_id}"
    collection = chromadb_client.get_or_create_collection(
        collection_name,
        metadata={"trilogy_id": trilogy_id, "character_id": character_id}
    )
    
    # Prepare documents
    docs = [
        {
            'id': f"{character_id}_profile",
            'text': f"Character: {character_data['name']}\n{character_data['description']}"
        },
        {
            'id': f"{character_id}_arc",
            'text': f"Arc: {character_data['character_arc']}"
        }
    ]
    
    # Embed and add
    texts = [d['text'] for d in docs]
    embeddings = embedding_service.embed_batch(texts)
    
    collection.add(
        ids=[d['id'] for d in docs],
        embeddings=embeddings.tolist(),
        documents=texts,
        metadatas=[{'character_id': character_id} for _ in docs]
    )
    
    chromadb_client.persist()
    return collection_name
```

### Query Character Context
```python
def get_character_context(trilogy_id, character_id, query_text, n_results=5):
    collection_name = f"{trilogy_id}_character_{character_id}"
    collection = chromadb_client.client.get_collection(collection_name)
    
    # Generate query embedding
    query_embedding = embedding_service.embed_text(query_text)
    
    # Query
    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=n_results
    )
    
    # Format
    return [{
        'text': results['documents'][0][i],
        'similarity': 1 - results['distances'][0][i]
    } for i in range(len(results['ids'][0]))]
```

---

## Epic 5B: World Rule RAG

### World Rule Embedding
```python
def initialize_world_rules(trilogy_id):
    collection_name = f"{trilogy_id}_world_rules"
    return chromadb_client.get_or_create_collection(
        collection_name,
        metadata={"trilogy_id": trilogy_id, "type": "world_rules"}
    )

def embed_world_rule(trilogy_id, rule_id, rule_data):
    collection_name = f"{trilogy_id}_world_rules"
    collection = chromadb_client.client.get_collection(collection_name)
    
    # Prepare text
    text = f"Title: {rule_data['title']}\nDescription: {rule_data['description']}\nCategory: {rule_data['category']}"
    
    # Embed
    embedding = embedding_service.embed_text(text)
    
    # Add
    collection.add(
        ids=[rule_id],
        embeddings=[embedding.tolist()],
        documents=[text],
        metadatas=[{
            'trilogy_id': trilogy_id,
            'rule_id': rule_id,
            'category': rule_data['category'],
            'book_ids': rule_data.get('book_ids', []),
            'accuracy': rule_data.get('accuracy', 1.0)
        }]
    )
    
    chromadb_client.persist()
```

### Query Relevant Rules
```python
def get_relevant_rules(trilogy_id, book_id, query_text, max_rules=10, threshold=0.65):
    collection_name = f"{trilogy_id}_world_rules"
    collection = chromadb_client.client.get_collection(collection_name)
    
    # Query
    query_embedding = embedding_service.embed_text(query_text)
    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=max_rules * 2  # Request extra for filtering
    )
    
    # Filter by book and threshold
    filtered = []
    for i in range(len(results['ids'][0])):
        similarity = 1 - results['distances'][0][i]
        metadata = results['metadatas'][0][i]
        
        # Check book association
        if book_id not in metadata.get('book_ids', []):
            continue
        
        # Check threshold
        if similarity < threshold:
            continue
        
        # Apply accuracy weighting
        accuracy = metadata.get('accuracy', 1.0)
        adjusted_similarity = similarity * (0.7 if accuracy < 0.5 else 1.0)
        
        filtered.append({
            'rule_id': metadata['rule_id'],
            'text': results['documents'][0][i],
            'similarity': similarity,
            'adjusted_similarity': adjusted_similarity
        })
    
    # Sort and return top N
    filtered.sort(key=lambda x: x['adjusted_similarity'], reverse=True)
    return filtered[:max_rules]
```

---

## Combined RAG Generation

### Generate with Both Character & World Rules
```python
import asyncio
import httpx

async def generate_content(
    trilogy_id, book_id, character_id, prompt, plot_points,
    bedrock_api_url, target_word_count=2000
):
    # Parallel retrieval
    query_text = f"{prompt}\n{plot_points}"
    
    character_context, world_rules = await asyncio.gather(
        asyncio.to_thread(get_character_context, trilogy_id, character_id, query_text),
        asyncio.to_thread(get_relevant_rules, trilogy_id, book_id, query_text)
    )
    
    # Build prompt
    prompt_parts = []
    
    # Character context
    if character_context:
        context_text = "\n\n".join([ctx['text'] for ctx in character_context])
        prompt_parts.append(f"CHARACTER VOICE:\n{context_text}")
    
    # World rules
    if world_rules:
        rules_text = "\n".join([
            f"{i+1}. {rule['text']}"
            for i, rule in enumerate(world_rules)
        ])
        prompt_parts.append(f"WORLD RULES:\n{rules_text}")
    
    # Task
    prompt_parts.append(f"TASK:\n{prompt}\n\nPLOT:\n{plot_points}\n\nTARGET: {target_word_count} words")
    
    enhanced_prompt = "\n\n".join(prompt_parts)
    
    # Call Bedrock
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            bedrock_api_url,
            json={
                "prompt": enhanced_prompt,
                "max_tokens": target_word_count * 2,
                "temperature": 0.7
            }
        )
        result = response.json()
        return result['generated_text']
```

---

## FastAPI Endpoint

```python
# app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class GenerateRequest(BaseModel):
    trilogy_id: str
    book_id: int
    character_id: str
    prompt: str
    plot_points: str
    target_word_count: int = 2000

@app.post("/api/generate")
async def generate(req: GenerateRequest):
    try:
        content = await generate_content(
            trilogy_id=req.trilogy_id,
            book_id=req.book_id,
            character_id=req.character_id,
            prompt=req.prompt,
            plot_points=req.plot_points,
            bedrock_api_url="https://YOUR_API.execute-api.ca-central-1.amazonaws.com/prod/generate",
            target_word_count=req.target_word_count
        )
        return {"generated_content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Environment Variables

```bash
# .env
CHROMADB_PERSIST_DIR=/Volumes/ExternalSSD/consciousness_trilogy/chromadb
BEDROCK_API_URL=https://YOUR_API_ID.execute-api.ca-central-1.amazonaws.com/prod/generate
AWS_REGION=ca-central-1
```

---

## Testing Commands

```bash
# Test embedding service
python -c "
from app.services.embedding_service import embedding_service
emb = embedding_service.embed_text('test')
print(f'Dimension: {len(emb)}')
"

# Test ChromaDB
python -c "
from app.services.chromadb_client import chromadb_client
collections = chromadb_client.list_collections()
print(f'Collections: {collections}')
"

# Test AWS endpoint
curl -X POST https://YOUR_API.execute-api.ca-central-1.amazonaws.com/prod/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"test","max_tokens":100,"temperature":0.7}'
```

---

## Memory Usage on 8GB MacBook

```
Component                Memory Usage
─────────────────────────────────────
Streamlit                ~300 MB
FastAPI                  ~300 MB
ChromaDB                 ~200 MB
Embedding Model          ~500 MB
─────────────────────────────────────
TOTAL LOCAL              ~1.3 GB

External (no local memory):
- Supabase (hosted)
- AWS Bedrock (cloud)
- Storage (external SSD)
```

You have **plenty of headroom** on 8GB MacBook! ✓

---

## Common Issues

**ChromaDB: Collection not found**
```python
# Initialize first
collection = chromadb_client.get_or_create_collection(collection_name)
```

**AWS: Permission denied**
```bash
# Verify IAM role
aws iam get-role-policy --role-name ConsciousnessTrilogyLambdaRole --policy-name BedrockAccessPolicy
```

**Embedding: Model download slow**
```python
# Download once manually
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder='./models')
```

---

## Next Steps

1. ✓ Duplicate AWS setup
2. ✓ Install sentence-transformers
3. ✓ Create embedding services
4. ✓ Implement Character RAG (Epic 5A)
5. ✓ Implement World Rule RAG (Epic 5B)
6. ☐ Add Redis caching
7. ☐ Implement pg-boss async jobs
8. ☐ Build Streamlit UI
9. ☐ Deploy to production

---

**Quick Reference Version:** 1.0  
**Created:** November 2, 2025
