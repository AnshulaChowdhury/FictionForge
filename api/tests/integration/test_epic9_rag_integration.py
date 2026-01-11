"""
Integration tests for Epic 9 RAG System
Tests the complete flow: embedding generation → ChromaDB storage → similarity search
"""

import pytest
import tempfile
import shutil
import os
from services.embedding_service import embedding_service
from services.chromadb_client import ChromaDBClient


@pytest.fixture
def temp_chromadb_dir():
    """Create a temporary directory for integration testing"""
    temp_dir = tempfile.mkdtemp(prefix="integration_test_chromadb_")
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def integration_chromadb_client(temp_chromadb_dir, monkeypatch):
    """Create a ChromaDB client for integration testing"""
    monkeypatch.setenv('CHROMADB_PERSIST_DIR', temp_chromadb_dir)
    client = ChromaDBClient()
    yield client
    # Cleanup
    try:
        collections = client.list_collections()
        for collection_name in collections:
            client.delete_collection(collection_name)
    except:
        pass


class TestCharacterRAGWorkflow:
    """Integration tests for Character RAG workflow (Epic 5A foundation)"""

    def test_character_embedding_workflow(self, integration_chromadb_client):
        """Test complete workflow: create character embeddings and query"""
        # Simulate character data
        trilogy_id = "test_trilogy_001"
        character_id = "test_character_001"
        collection_name = f"{trilogy_id}_character_{character_id}"

        # Character profile data
        character_documents = [
            "Character Profile: Dr. Sarah Chen, a brilliant neuroscientist who questions consciousness",
            "Character Traits: analytical, empathetic, skeptical of AI consciousness theories",
            "Character Arc: Begins as materialist, evolves to accept transcendent consciousness",
            "Consciousness Themes: mind-body problem, emergence, personal identity"
        ]

        # Step 1: Generate embeddings
        embeddings = embedding_service.embed_batch(character_documents)

        assert embeddings.shape == (len(character_documents), 384)

        # Step 2: Create collection
        collection = integration_chromadb_client.get_or_create_collection(
            collection_name,
            metadata={
                "trilogy_id": trilogy_id,
                "character_id": character_id,
                "type": "character_context"
            }
        )

        # Step 3: Add documents to collection
        ids = [f"{character_id}_{i}" for i in range(len(character_documents))]
        collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=character_documents,
            metadatas=[{"doc_type": f"type_{i}"} for i in range(len(character_documents))]
        )

        # Step 4: Query for relevant character context
        query_text = "Write about a scientist's philosophical views on consciousness"
        query_embedding = embedding_service.embed_text(query_text)

        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=2
        )

        # Verify results
        assert len(results['ids'][0]) == 2
        assert len(results['documents'][0]) == 2

        # Character profile should be in top results
        retrieved_docs = results['documents'][0]
        assert any("consciousness" in doc.lower() for doc in retrieved_docs)

    def test_multiple_character_isolation(self, integration_chromadb_client):
        """Test that different characters have isolated vector stores"""
        trilogy_id = "test_trilogy_002"
        character1_id = "char_001"
        character2_id = "char_002"

        # Create separate collections for each character
        collection1_name = f"{trilogy_id}_character_{character1_id}"
        collection2_name = f"{trilogy_id}_character_{character2_id}"

        collection1 = integration_chromadb_client.get_or_create_collection(collection1_name)
        collection2 = integration_chromadb_client.get_or_create_collection(collection2_name)

        # Add different data to each collection
        char1_docs = ["Character 1 is an optimist", "Character 1 loves science"]
        char2_docs = ["Character 2 is a pessimist", "Character 2 fears technology"]

        char1_embeddings = embedding_service.embed_batch(char1_docs)
        char2_embeddings = embedding_service.embed_batch(char2_docs)

        collection1.add(
            ids=["doc1", "doc2"],
            embeddings=char1_embeddings.tolist(),
            documents=char1_docs
        )

        collection2.add(
            ids=["doc1", "doc2"],
            embeddings=char2_embeddings.tolist(),
            documents=char2_docs
        )

        # Query character 1's collection
        query = "Tell me about optimistic views"
        query_emb = embedding_service.embed_text(query)

        results1 = collection1.query(query_embeddings=[query_emb.tolist()], n_results=1)

        # Should retrieve character 1's data
        assert "optimist" in results1['documents'][0][0].lower()

        # Verify collections are isolated
        count1 = integration_chromadb_client.get_collection_count(collection1_name)
        count2 = integration_chromadb_client.get_collection_count(collection2_name)

        assert count1 == 2
        assert count2 == 2


class TestWorldRuleRAGWorkflow:
    """Integration tests for World Rule RAG workflow (Epic 5B foundation)"""

    def test_world_rule_embedding_workflow(self, integration_chromadb_client):
        """Test complete workflow: embed world rules and query"""
        trilogy_id = "test_trilogy_003"
        collection_name = f"{trilogy_id}_world_rules"

        # World rules
        rules = [
            {
                "id": "rule_001",
                "title": "Consciousness Transfer Limitation",
                "description": "Consciousness can only be transferred with quantum precision mapping. Any loss >0.1% causes personality degradation.",
                "category": "consciousness_mechanics",
                "book_ids": [1, 2, 3]
            },
            {
                "id": "rule_002",
                "title": "Mars Atmospheric Pressure",
                "description": "Mars atmospheric pressure is 0.6% of Earth's. Habitats must maintain 1 atm pressure with redundant systems.",
                "category": "environment",
                "book_ids": [1, 2, 3]
            },
            {
                "id": "rule_003",
                "title": "AI Rights Timeline",
                "description": "AI gained legal personhood in 2087 after Singapore Accord. Before this, AIs had no legal standing.",
                "category": "society",
                "book_ids": [2, 3]
            }
        ]

        # Prepare rule texts for embedding
        rule_texts = [
            f"Title: {r['title']}\nDescription: {r['description']}\nCategory: {r['category']}"
            for r in rules
        ]

        # Step 1: Generate embeddings
        embeddings = embedding_service.embed_batch(rule_texts)

        # Step 2: Create collection
        collection = integration_chromadb_client.get_or_create_collection(
            collection_name,
            metadata={"trilogy_id": trilogy_id, "type": "world_rules"}
        )

        # Step 3: Add rules to collection
        collection.add(
            ids=[r['id'] for r in rules],
            embeddings=embeddings.tolist(),
            documents=rule_texts,
            metadatas=[
                {
                    "category": r['category'],
                    "book_ids": r['book_ids'],
                    "rule_id": r['id']
                }
                for r in rules
            ]
        )

        # Step 4: Query for relevant rules
        query_text = "Write about transferring consciousness to a new body"
        query_embedding = embedding_service.embed_text(query_text)

        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=2
        )

        # Verify results
        assert len(results['ids'][0]) >= 1

        # Consciousness transfer rule should be in results
        retrieved_docs = results['documents'][0]
        assert any("consciousness" in doc.lower() and "transfer" in doc.lower() for doc in retrieved_docs)

    def test_world_rule_filtering_by_book(self, integration_chromadb_client):
        """Test filtering world rules by book association"""
        trilogy_id = "test_trilogy_004"
        collection_name = f"{trilogy_id}_world_rules"

        # Create rules with different book associations
        rules_data = [
            ("rule_book1", "Rule for book 1 only", [1]),
            ("rule_book2", "Rule for book 2 only", [2]),
            ("rule_book3", "Rule for book 3 only", [3]),
            ("rule_all_books", "Rule for all books", [1, 2, 3])
        ]

        rule_texts = [f"Rule: {text}" for _, text, _ in rules_data]
        embeddings = embedding_service.embed_batch(rule_texts)

        collection = integration_chromadb_client.get_or_create_collection(collection_name)

        collection.add(
            ids=[rule_id for rule_id, _, _ in rules_data],
            embeddings=embeddings.tolist(),
            documents=rule_texts,
            metadatas=[
                {"book_ids": book_ids, "rule_id": rule_id}
                for rule_id, _, book_ids in rules_data
            ]
        )

        # Query and filter results manually (simulating book filtering)
        query_emb = embedding_service.embed_text("Tell me about rules")
        results = collection.query(
            query_embeddings=[query_emb.tolist()],
            n_results=10
        )

        # Filter for book 1
        book1_rules = [
            results['ids'][0][i]
            for i in range(len(results['ids'][0]))
            if 1 in results['metadatas'][0][i]['book_ids']
        ]

        # Should include rule_book1 and rule_all_books
        assert "rule_book1" in book1_rules
        assert "rule_all_books" in book1_rules
        assert "rule_book2" not in book1_rules


class TestCombinedRAGWorkflow:
    """Integration tests for combined Character + World Rule RAG"""

    def test_parallel_context_retrieval(self, integration_chromadb_client):
        """Test retrieving both character context and world rules simultaneously"""
        trilogy_id = "test_trilogy_005"
        character_id = "char_005"

        # Create character collection
        char_collection_name = f"{trilogy_id}_character_{character_id}"
        char_collection = integration_chromadb_client.get_or_create_collection(char_collection_name)

        character_docs = [
            "Character: Dr. Alex Rivera, physicist studying consciousness transfer",
            "Personality: Cautious, ethical, concerned about identity preservation"
        ]

        char_embeddings = embedding_service.embed_batch(character_docs)
        char_collection.add(
            ids=["char_doc1", "char_doc2"],
            embeddings=char_embeddings.tolist(),
            documents=character_docs
        )

        # Create world rules collection
        rules_collection_name = f"{trilogy_id}_world_rules"
        rules_collection = integration_chromadb_client.get_or_create_collection(rules_collection_name)

        rule_docs = [
            "Rule: Consciousness transfer requires quantum state mapping",
            "Rule: Identity continuity requires 99.9% neural pattern preservation"
        ]

        rule_embeddings = embedding_service.embed_batch(rule_docs)
        rules_collection.add(
            ids=["rule1", "rule2"],
            embeddings=rule_embeddings.tolist(),
            documents=rule_docs
        )

        # Query both collections with same prompt
        prompt = "Write about a physicist's concerns during consciousness transfer"
        query_emb = embedding_service.embed_text(prompt)

        # Retrieve from both collections
        char_results = char_collection.query(
            query_embeddings=[query_emb.tolist()],
            n_results=2
        )

        rule_results = rules_collection.query(
            query_embeddings=[query_emb.tolist()],
            n_results=2
        )

        # Verify both returned results
        assert len(char_results['documents'][0]) > 0
        assert len(rule_results['documents'][0]) > 0

        # Character context should mention physicist
        char_text = " ".join(char_results['documents'][0])
        assert "physicist" in char_text.lower()

        # Rule context should mention consciousness transfer
        rule_text = " ".join(rule_results['documents'][0])
        assert "consciousness" in rule_text.lower()


class TestRAGPersistence:
    """Integration tests for RAG data persistence"""

    def test_embeddings_persist_across_sessions(self, temp_chromadb_dir, monkeypatch):
        """Test that embedded data persists when client restarts"""
        monkeypatch.setenv('CHROMADB_PERSIST_DIR', temp_chromadb_dir)

        # Session 1: Create and populate collection
        client1 = ChromaDBClient()
        collection_name = "persistent_test"
        collection = client1.get_or_create_collection(collection_name)

        documents = ["Persistent document 1", "Persistent document 2"]
        embeddings = embedding_service.embed_batch(documents)

        collection.add(
            ids=["doc1", "doc2"],
            embeddings=embeddings.tolist(),
            documents=documents
        )

        client1.persist()

        # Session 2: Create new client and verify data exists
        client2 = ChromaDBClient()
        count = client2.get_collection_count(collection_name)

        assert count == 2, "Data should persist across client instances"

        # Query and verify documents are retrievable
        collection2 = client2.get_collection(collection_name)
        query_emb = embedding_service.embed_text("persistent")

        results = collection2.query(
            query_embeddings=[query_emb.tolist()],
            n_results=2
        )

        assert len(results['documents'][0]) == 2


class TestRAGPerformance:
    """Integration tests for RAG system performance"""

    def test_large_batch_embedding_and_storage(self, integration_chromadb_client):
        """Test handling large batches of documents"""
        collection_name = "large_batch_test"
        collection = integration_chromadb_client.get_or_create_collection(collection_name)

        # Generate 100 documents
        num_docs = 100
        documents = [f"Document number {i} with some test content" for i in range(num_docs)]

        # Embed in batch
        embeddings = embedding_service.embed_batch(documents, batch_size=32)

        assert embeddings.shape == (num_docs, 384)

        # Add to collection
        ids = [f"doc_{i}" for i in range(num_docs)]
        collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=documents
        )

        # Verify count
        count = integration_chromadb_client.get_collection_count(collection_name)
        assert count == num_docs

        # Query should work efficiently
        query_emb = embedding_service.embed_text("test content")
        results = collection.query(
            query_embeddings=[query_emb.tolist()],
            n_results=10
        )

        assert len(results['ids'][0]) == 10

    def test_similarity_search_accuracy(self, integration_chromadb_client):
        """Test that similarity search returns relevant results"""
        collection_name = "similarity_test"
        collection = integration_chromadb_client.get_or_create_collection(collection_name)

        # Add diverse documents
        documents = [
            "The cat sat on the mat and purred contentedly",
            "Dogs are loyal and friendly companions",
            "Quantum computing uses qubits for parallel processing",
            "Mars colonization requires advanced life support systems",
            "A feline rested comfortably on the rug"
        ]

        embeddings = embedding_service.embed_batch(documents)
        ids = [f"doc_{i}" for i in range(len(documents))]

        collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=documents
        )

        # Query with text similar to doc 0 and doc 4
        query = "Tell me about cats sitting on carpets"
        query_emb = embedding_service.embed_text(query)

        results = collection.query(
            query_embeddings=[query_emb.tolist()],
            n_results=2
        )

        # Top results should be about cats
        retrieved_docs = results['documents'][0]
        assert any("cat" in doc.lower() or "feline" in doc.lower() for doc in retrieved_docs)

        # Should not retrieve quantum computing or Mars docs
        assert not any("quantum" in doc.lower() for doc in retrieved_docs)
        assert not any("mars" in doc.lower() for doc in retrieved_docs[:2])


class TestRAGErrorHandling:
    """Integration tests for error handling in RAG workflows"""

    def test_query_empty_collection(self, integration_chromadb_client):
        """Test querying an empty collection"""
        collection_name = "empty_collection"
        collection = integration_chromadb_client.get_or_create_collection(collection_name)

        query_emb = embedding_service.embed_text("test query")

        # Should not raise error, just return empty results
        results = collection.query(
            query_embeddings=[query_emb.tolist()],
            n_results=5
        )

        assert len(results['ids'][0]) == 0

    def test_add_documents_with_mismatched_lengths(self, integration_chromadb_client):
        """Test error handling for mismatched document and embedding lengths"""
        collection_name = "mismatch_test"
        collection = integration_chromadb_client.get_or_create_collection(collection_name)

        documents = ["Doc 1", "Doc 2"]
        embeddings = embedding_service.embed_batch(["Doc 1"])  # Only one embedding

        # Should raise error
        with pytest.raises(Exception):
            collection.add(
                ids=["doc1", "doc2"],
                embeddings=embeddings.tolist(),
                documents=documents
            )
