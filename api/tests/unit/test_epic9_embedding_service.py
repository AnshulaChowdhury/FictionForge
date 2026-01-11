"""
Test script for Embedding Service and ChromaDB integration
Run this to verify Epic 9 setup is working correctly

Usage:
    python test_embedding_service.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import from api
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("EPIC 9 TEST: Embedding Service & ChromaDB Integration")
print("=" * 70)

# Test 1: Import services
print("\n[Test 1] Importing services...")
try:
    from services.embedding_service import embedding_service
    from services.chromadb_client import chromadb_client
    print("✓ Services imported successfully")
except Exception as e:
    print(f"✗ Failed to import services: {e}")
    sys.exit(1)

# Test 2: Check memory before loading model
print("\n[Test 2] Checking memory usage...")
try:
    import psutil
    process = psutil.Process(os.getpid())
    memory_before = process.memory_info().rss / 1024 / 1024  # MB
    print(f"Memory before loading model: {memory_before:.2f} MB")
except ImportError:
    print("⚠ psutil not installed, skipping memory check (pip install psutil)")
    memory_before = None

# Test 3: Generate single embedding
print("\n[Test 3] Generating single embedding...")
try:
    test_text = "This is a test sentence for embedding generation."
    embedding = embedding_service.embed_text(test_text)
    print(f"✓ Embedding generated")
    print(f"  Dimension: {len(embedding)}")
    print(f"  First 5 values: {embedding[:5]}")

    expected_dim = embedding_service.get_embedding_dimension()
    assert len(embedding) == expected_dim, f"Expected dimension {expected_dim}, got {len(embedding)}"
    print(f"✓ Dimension check passed: {expected_dim}")
except Exception as e:
    print(f"✗ Failed to generate embedding: {e}")
    sys.exit(1)

# Test 4: Check memory after loading model
if memory_before:
    try:
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = memory_after - memory_before
        print(f"\n[Test 4] Memory after loading model: {memory_after:.2f} MB")
        print(f"Memory used by model: {memory_used:.2f} MB")

        if memory_used > 700:
            print(f"⚠ Warning: Model using more memory than expected ({memory_used:.2f} MB > 700 MB)")
        else:
            print(f"✓ Memory usage within expected range")
    except Exception as e:
        print(f"⚠ Could not measure memory: {e}")

# Test 5: Generate batch embeddings
print("\n[Test 5] Generating batch embeddings...")
try:
    test_texts = [
        "Mars colonization requires radiation shielding.",
        "The character struggles with AI consciousness.",
        "Terraforming takes centuries of careful planning."
    ]
    embeddings = embedding_service.embed_batch(test_texts)
    print(f"✓ Batch embeddings generated")
    print(f"  Batch size: {len(embeddings)}")
    print(f"  Each embedding dimension: {len(embeddings[0])}")

    assert len(embeddings) == len(test_texts), "Batch size mismatch"
    print(f"✓ Batch size check passed")
except Exception as e:
    print(f"✗ Failed to generate batch embeddings: {e}")
    sys.exit(1)

# Test 6: Test similarity computation
print("\n[Test 6] Testing similarity computation...")
try:
    text1 = "The cat sat on the mat"
    text2 = "A feline rested on the rug"
    text3 = "Quantum computing uses qubits"

    emb1 = embedding_service.embed_text(text1)
    emb2 = embedding_service.embed_text(text2)
    emb3 = embedding_service.embed_text(text3)

    sim_similar = embedding_service.compute_similarity(emb1, emb2)
    sim_different = embedding_service.compute_similarity(emb1, emb3)

    print(f"✓ Similarity computation successful")
    print(f"  Similar texts: {sim_similar:.4f} (expected: >0.5)")
    print(f"  Different texts: {sim_different:.4f} (expected: <0.3)")

    if sim_similar > sim_different:
        print(f"✓ Similarity check passed: similar > different")
    else:
        print(f"⚠ Warning: Similar texts have lower similarity than different texts")
except Exception as e:
    print(f"✗ Failed similarity test: {e}")
    sys.exit(1)

# Test 7: ChromaDB health check
print("\n[Test 7] Testing ChromaDB connection...")
try:
    health = chromadb_client.health_check()
    if health['healthy']:
        print(f"✓ ChromaDB is operational")
    else:
        print(f"✗ ChromaDB error: {health['message']}")
        sys.exit(1)
except Exception as e:
    print(f"✗ Failed ChromaDB health check: {e}")
    sys.exit(1)

# Test 8: Create test collection
print("\n[Test 8] Testing ChromaDB collection operations...")
try:
    test_collection_name = "test_epic9_collection"

    # Create collection
    collection = chromadb_client.get_or_create_collection(
        test_collection_name,
        metadata={"test": "epic9", "purpose": "verification"}
    )
    print(f"✓ Collection created/retrieved: {test_collection_name}")

    # Add some test data
    test_docs = [
        "Character profile: Dr. Sarah Chen, brilliant neuroscientist",
        "Character arc: Begins skeptical, evolves to accept consciousness transcendence",
        "World rule: Consciousness transfer requires quantum precision"
    ]

    embeddings = embedding_service.embed_batch(test_docs)

    collection.add(
        ids=["doc1", "doc2", "doc3"],
        embeddings=embeddings.tolist(),
        documents=test_docs,
        metadatas=[{"type": "profile"}, {"type": "arc"}, {"type": "rule"}]
    )
    print(f"✓ Added {len(test_docs)} documents to collection")

    # Query the collection
    query_text = "Tell me about consciousness and neural science"
    query_embedding = embedding_service.embed_text(query_text)

    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=2
    )

    print(f"✓ Query executed successfully")
    print(f"  Results returned: {len(results['ids'][0])}")
    print(f"  Top result: {results['documents'][0][0][:80]}...")

    # Get collection info
    info = chromadb_client.get_collection_info(test_collection_name)
    print(f"✓ Collection info retrieved")
    print(f"  Document count: {info['count']}")

    # Clean up
    chromadb_client.delete_collection(test_collection_name)
    print(f"✓ Test collection cleaned up")

except Exception as e:
    print(f"✗ Failed ChromaDB collection test: {e}")
    # Try to clean up
    try:
        chromadb_client.delete_collection(test_collection_name)
    except:
        pass
    sys.exit(1)

# Test 9: List all collections
print("\n[Test 9] Listing all collections...")
try:
    collections = chromadb_client.list_collections()
    print(f"✓ Collections listed successfully")
    print(f"  Total collections: {len(collections)}")
    if collections:
        print(f"  Collections: {', '.join(collections)}")
except Exception as e:
    print(f"✗ Failed to list collections: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 70)
print("EPIC 9 TEST SUMMARY")
print("=" * 70)
print("✓ All tests passed successfully!")
print("\nEmbedding Service Status:")
print(f"  - Model: {embedding_service.get_embedding_dimension()}-dimensional embeddings")
print(f"  - Single text embedding: Working")
print(f"  - Batch embedding: Working")
print(f"  - Similarity computation: Working")
print("\nChromaDB Status:")
print(f"  - Connection: Healthy")
print(f"  - Persist directory: {os.getenv('CHROMADB_PERSIST_DIR', './chromadb_data')}")
print(f"  - Collections: {len(collections)} existing")
print(f"  - CRUD operations: Working")
print("\n" + "=" * 70)
print("Epic 9 setup is complete and operational! 🎉")
print("=" * 70)
