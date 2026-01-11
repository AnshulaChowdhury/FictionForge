"""
Character Embedding Service for Epic 5A

Handles character profile embedding into ChromaDB collections for
character-specific RAG content generation.
"""

import json
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime
from uuid import UUID

from api.services.chromadb_client import get_chromadb_client
from api.services.embedding_service import get_embedding_service
from api.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class CharacterEmbeddingError(Exception):
    """Raised when character embedding fails"""
    pass


class CharacterEmbeddingService:
    """Handles character data embedding into ChromaDB"""

    def __init__(self):
        self.chromadb = get_chromadb_client()
        self.embedding_service = get_embedding_service()
        self.supabase = get_supabase_client()

    def get_collection_name(self, trilogy_id: str, character_id: str) -> str:
        """
        Generate ChromaDB collection name for a character.

        Args:
            trilogy_id: Trilogy identifier
            character_id: Character identifier

        Returns:
            Collection name in format: {trilogy_id}_character_{character_id}
        """
        return f"{trilogy_id}_character_{character_id}"

    async def embed_character(
        self,
        character_id: str,
        trilogy_id: str,
        name: str,
        description: str = None,
        traits: Dict[str, Any] = None,
        character_arc: str = None,
        consciousness_themes: List[str] = None
    ) -> Dict[str, Any]:
        """
        Embed character data into a dedicated ChromaDB collection.

        Creates a new collection for the character and embeds:
        - Character profile (name, description)
        - Character traits
        - Character arc
        - Consciousness themes

        Args:
            character_id: Character identifier
            trilogy_id: Trilogy identifier
            name: Character name
            description: Character description
            traits: Character traits dictionary
            character_arc: Character arc description
            consciousness_themes: List of consciousness themes

        Returns:
            Dict with status, collection_name, and document_count

        Raises:
            CharacterEmbeddingError: If embedding fails
        """
        try:
            collection_name = self.get_collection_name(trilogy_id, character_id)

            logger.info(f"Creating collection for character {character_id}: {collection_name}")

            # Get or create collection
            collection = await self._get_or_create_collection(
                collection_name,
                character_id,
                trilogy_id,
                name
            )

            # Prepare documents for embedding
            documents, ids, metadatas = self._prepare_character_documents(
                character_id=character_id,
                name=name,
                description=description,
                traits=traits,
                character_arc=character_arc,
                consciousness_themes=consciousness_themes
            )

            # Add documents to collection
            collection.add(
                documents=documents,
                ids=ids,
                metadatas=metadatas
            )

            logger.info(
                f"Successfully embedded {len(documents)} documents for character {character_id}"
            )

            return {
                "status": "success",
                "collection_name": collection_name,
                "document_count": len(documents),
                "character_id": character_id
            }

        except Exception as e:
            logger.error(f"Failed to embed character {character_id}: {e}")
            raise CharacterEmbeddingError(f"Embedding failed: {str(e)}")

    async def update_character_embedding(
        self,
        character_id: str,
        trilogy_id: str,
        name: str,
        description: str = None,
        traits: Dict[str, Any] = None,
        character_arc: str = None,
        consciousness_themes: List[str] = None
    ) -> Dict[str, Any]:
        """
        Update character embedding by re-embedding profile documents.

        This deletes old profile documents and re-embeds them with updated data.

        Args:
            character_id: Character identifier
            trilogy_id: Trilogy identifier
            name: Updated character name
            description: Updated character description
            traits: Updated character traits
            character_arc: Updated character arc
            consciousness_themes: Updated consciousness themes

        Returns:
            Dict with status and document_count

        Raises:
            CharacterEmbeddingError: If update fails
        """
        try:
            collection_name = self.get_collection_name(trilogy_id, character_id)
            collection = self.chromadb.get_collection(collection_name)

            # Delete old profile documents
            old_ids = [
                f"{character_id}_profile",
                f"{character_id}_traits",
                f"{character_id}_arc",
                f"{character_id}_themes"
            ]

            try:
                collection.delete(ids=old_ids)
            except Exception as e:
                logger.warning(f"Error deleting old documents: {e}")

            # Prepare and add updated documents
            documents, ids, metadatas = self._prepare_character_documents(
                character_id=character_id,
                name=name,
                description=description,
                traits=traits,
                character_arc=character_arc,
                consciousness_themes=consciousness_themes
            )

            collection.add(
                documents=documents,
                ids=ids,
                metadatas=metadatas
            )

            # Update collection metadata
            collection.modify(metadata={
                **collection.metadata,
                "last_updated": datetime.utcnow().isoformat(),
                "character_name": name
            })

            logger.info(f"Successfully updated embedding for character {character_id}")

            return {
                "status": "success",
                "collection_name": collection_name,
                "document_count": len(documents)
            }

        except Exception as e:
            logger.error(f"Failed to update character embedding {character_id}: {e}")
            raise CharacterEmbeddingError(f"Update failed: {str(e)}")

    async def delete_character_embedding(
        self,
        character_id: str,
        trilogy_id: str
    ) -> bool:
        """
        Delete character's ChromaDB collection.

        Args:
            character_id: Character identifier
            trilogy_id: Trilogy identifier

        Returns:
            True if successful

        Raises:
            CharacterEmbeddingError: If deletion fails
        """
        try:
            collection_name = self.get_collection_name(trilogy_id, character_id)

            self.chromadb.delete_collection(collection_name)

            logger.info(f"Deleted collection for character {character_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete character embedding {character_id}: {e}")
            raise CharacterEmbeddingError(f"Deletion failed: {str(e)}")

    async def add_generated_content(
        self,
        character_id: str,
        trilogy_id: str,
        sub_chapter_id: str,
        content: str,
        version_number: int = 1
    ) -> bool:
        """
        Add newly generated content to character's ChromaDB collection.

        This builds the character's content history for future RAG retrieval.

        Args:
            character_id: Character identifier
            trilogy_id: Trilogy identifier
            sub_chapter_id: Sub-chapter identifier
            content: Generated content text
            version_number: Version number

        Returns:
            True if successful, False otherwise
        """
        try:
            collection_name = self.get_collection_name(trilogy_id, character_id)
            collection = self.chromadb.get_collection(collection_name)

            # Generate document ID
            doc_id = f"{character_id}_subchapter_{sub_chapter_id}_v{version_number}"

            # Add to collection
            collection.add(
                documents=[content],
                ids=[doc_id],
                metadatas=[{
                    "type": "generated_content",
                    "character_id": character_id,
                    "sub_chapter_id": sub_chapter_id,
                    "version_number": version_number,
                    "word_count": len(content.split()),
                    "generated_at": datetime.utcnow().isoformat()
                }]
            )

            # Update collection metadata
            collection.modify(metadata={
                **collection.metadata,
                "document_count": collection.count(),
                "last_updated": datetime.utcnow().isoformat()
            })

            logger.info(f"Added generated content to character {character_id}: {doc_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to add generated content for character {character_id}: {e}")
            # Don't raise - allow generation to complete even if context update fails
            return False

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _get_or_create_collection(
        self,
        collection_name: str,
        character_id: str,
        trilogy_id: str,
        character_name: str
    ):
        """
        Get existing collection or create a new one.

        Args:
            collection_name: Collection name
            character_id: Character identifier
            trilogy_id: Trilogy identifier
            character_name: Character name

        Returns:
            ChromaDB collection
        """
        try:
            # Try to get existing collection
            collection = self.chromadb.get_collection(collection_name)
            logger.info(f"Using existing collection: {collection_name}")
            return collection

        except Exception:
            # Create new collection
            logger.info(f"Creating new collection: {collection_name}")
            return self.chromadb.create_collection(
                name=collection_name,
                metadata={
                    "trilogy_id": trilogy_id,
                    "character_id": character_id,
                    "character_name": character_name,
                    "created_at": datetime.utcnow().isoformat(),
                    "document_count": 0
                }
            )

    def _prepare_character_documents(
        self,
        character_id: str,
        name: str,
        description: str = None,
        traits: Dict[str, Any] = None,
        character_arc: str = None,
        consciousness_themes: List[str] = None
    ) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
        """
        Prepare character profile documents for embedding.

        Args:
            character_id: Character identifier
            name: Character name
            description: Character description
            traits: Character traits
            character_arc: Character arc
            consciousness_themes: Consciousness themes

        Returns:
            Tuple of (documents, ids, metadatas)
        """
        documents = []
        ids = []
        metadatas = []

        # Document 1: Character Profile
        if description:
            profile_text = f"Character Profile: {name}\n\n{description}"
            documents.append(profile_text)
            ids.append(f"{character_id}_profile")
            metadatas.append({
                "type": "profile",
                "character_id": character_id,
                "character_name": name
            })

        # Document 2: Character Traits
        if traits:
            traits_text = f"Character Traits for {name}:\n\n{json.dumps(traits, indent=2)}"
            documents.append(traits_text)
            ids.append(f"{character_id}_traits")
            metadatas.append({
                "type": "traits",
                "character_id": character_id,
                "character_name": name
            })

        # Document 3: Character Arc
        if character_arc:
            arc_text = f"Character Arc for {name}:\n\n{character_arc}"
            documents.append(arc_text)
            ids.append(f"{character_id}_arc")
            metadatas.append({
                "type": "arc",
                "character_id": character_id,
                "character_name": name
            })

        # Document 4: Consciousness Themes
        if consciousness_themes and len(consciousness_themes) > 0:
            themes_text = f"Consciousness Themes for {name}:\n\n{', '.join(consciousness_themes)}"
            documents.append(themes_text)
            ids.append(f"{character_id}_themes")
            metadatas.append({
                "type": "themes",
                "character_id": character_id,
                "character_name": name
            })

        return documents, ids, metadatas
