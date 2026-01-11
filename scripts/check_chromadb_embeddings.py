#!/usr/bin/env python3
"""
Script to check ChromaDB for world rule embeddings.

Run this from the project root to see if rules are embedded:
    python scripts/check_chromadb_embeddings.py <trilogy_id>
"""
import sys
import os

# Add project root and api directory to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'api'))

from api.services.chromadb_client import chromadb_client


def check_embeddings(trilogy_id: str):
    """Check ChromaDB for embeddings for a specific trilogy."""
    print("=" * 60)
    print(f"CHECKING CHROMADB EMBEDDINGS FOR TRILOGY: {trilogy_id}")
    print("=" * 60)

    collection_name = f"{trilogy_id}_world_rules"

    try:
        # Get collection
        collection = chromadb_client.get_collection(collection_name)
        print(f"\n✅ Collection Found: {collection_name}")

        # Get count
        count = collection.count()
        print(f"📊 Total Embeddings: {count}")

        if count > 0:
            # Get all documents
            results = collection.get(include=['metadatas', 'documents'])

            print(f"\n📋 Embedded Rules:")
            for idx, (doc_id, metadata, document) in enumerate(
                zip(results['ids'], results['metadatas'], results['documents']), 1
            ):
                print(f"\n{idx}. Rule ID: {metadata.get('rule_id', 'N/A')}")
                print(f"   Title: {metadata.get('title', 'N/A')}")
                print(f"   Category: {metadata.get('category', 'N/A')}")
                print(f"   Document: {document[:100]}...")

            # Test semantic search
            print(f"\n🔍 Testing Semantic Search:")
            test_query = "What are the rules about physics?"
            from api.services.embedding_service import embedding_service
            query_embedding = embedding_service.embed_text(test_query)

            search_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=3,
                include=['metadatas', 'distances']
            )

            if search_results['ids'] and search_results['ids'][0]:
                print(f"\nQuery: '{test_query}'")
                print(f"Top 3 Results:")
                for idx, (rule_id, metadata, distance) in enumerate(
                    zip(
                        search_results['ids'][0],
                        search_results['metadatas'][0],
                        search_results['distances'][0]
                    ), 1
                ):
                    similarity = 1 - (distance ** 2 / 2)  # Convert distance to similarity
                    print(f"  {idx}. {metadata.get('title', 'N/A')} (similarity: {similarity:.2f})")
            else:
                print("  No results found")

        else:
            print("\n⚠️  No embeddings found in this collection")
            print("   This means:")
            print("   1. No rules have been created yet, OR")
            print("   2. The Arq worker hasn't processed the jobs yet")

    except ValueError as e:
        print(f"\n❌ Collection Not Found: {collection_name}")
        print("   This means:")
        print("   1. No rules have been created for this trilogy yet, OR")
        print("   2. The Arq worker hasn't created the collection yet")
    except Exception as e:
        print(f"\n❌ Error: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_chromadb_embeddings.py <trilogy_id>")
        print("\nExample:")
        print("  python scripts/check_chromadb_embeddings.py 123e4567-e89b-12d3-a456-426614174000")
        sys.exit(1)

    trilogy_id = sys.argv[1]
    check_embeddings(trilogy_id)
