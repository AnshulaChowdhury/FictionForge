"""
World Rule Manager Service (Epic 3 - Phase 1).

Handles CRUD operations for world rules and book associations.
Integrates with ChromaDB for semantic search capabilities.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from api.utils.supabase_client import get_supabase_client
from api.models.world_rule import (
    WorldRuleCreate,
    WorldRuleUpdate,
    WorldRuleResponse,
    WorldRuleListResponse,
    CategoryListResponse,
)
import logging

logger = logging.getLogger(__name__)


class WorldRuleManager:
    """
    Manages world rules and their book associations.

    Responsibilities:
    - Create, read, update, delete world rules
    - Manage book associations via junction table
    - Track rule categories
    - Coordinate with embedding service for ChromaDB sync
    """

    def __init__(self):
        self.supabase = get_supabase_client()

    async def create_rule(
        self,
        rule_data: WorldRuleCreate,
        user_id: str
    ) -> WorldRuleResponse:
        """
        Create a new world rule with book associations.

        Args:
            rule_data: Rule creation data
            user_id: User creating the rule (for RLS validation)

        Returns:
            Created rule with book associations

        Raises:
            ValueError: If trilogy doesn't exist or books invalid
            Exception: If database operation fails
        """
        try:
            # 1. Verify trilogy exists and belongs to user
            trilogy_result = self.supabase.table('trilogy_projects').select('id, user_id').eq('id', rule_data.trilogy_id).execute()

            if not trilogy_result.data:
                raise ValueError(f"Trilogy {rule_data.trilogy_id} not found")

            if trilogy_result.data[0]['user_id'] != user_id:
                raise ValueError("Trilogy does not belong to user")

            # 2. Verify all books exist and belong to trilogy
            books_result = self.supabase.table('books').select('id, trilogy_id').in_('id', rule_data.book_ids).execute()

            if len(books_result.data) != len(rule_data.book_ids):
                found_ids = [b['id'] for b in books_result.data]
                missing_ids = set(rule_data.book_ids) - set(found_ids)
                raise ValueError(f"Books not found: {missing_ids}")

            # Verify all books belong to the trilogy
            for book in books_result.data:
                if book['trilogy_id'] != rule_data.trilogy_id:
                    raise ValueError(f"Book {book['id']} does not belong to trilogy {rule_data.trilogy_id}")

            # 3. Insert world rule
            rule_insert = {
                'trilogy_id': rule_data.trilogy_id,
                'title': rule_data.title,
                'description': rule_data.description,
                'category': rule_data.category,
                'times_flagged': 0,
                'times_true_violation': 0,
                'times_false_positive': 0,
                'times_intentional_break': 0,
                'times_checker_error': 0,
            }

            rule_result = self.supabase.table('world_rules').insert(rule_insert).execute()

            if not rule_result.data:
                raise Exception("Failed to create world rule")

            rule_id = rule_result.data[0]['id']
            logger.info(f"Created world rule {rule_id} for trilogy {rule_data.trilogy_id}")

            # 4. Insert book associations
            book_associations = [
                {
                    'world_rule_id': rule_id,
                    'book_id': book_id
                }
                for book_id in rule_data.book_ids
            ]

            associations_result = self.supabase.table('world_rule_books').insert(book_associations).execute()

            if not associations_result.data:
                # Rollback: delete the rule
                await self._delete_rule_by_id(rule_id)
                raise Exception("Failed to create book associations")

            logger.info(f"Created {len(book_associations)} book associations for rule {rule_id}")

            # 5. Return created rule with associations
            return await self.get_rule_by_id(rule_id, user_id)

        except ValueError as e:
            logger.error(f"Validation error creating rule: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating rule: {e}")
            raise Exception(f"Failed to create world rule: {str(e)}")

    async def get_rule_by_id(
        self,
        rule_id: str,
        user_id: str
    ) -> WorldRuleResponse:
        """
        Get a single world rule by ID with book associations.

        Args:
            rule_id: Rule identifier
            user_id: User requesting the rule (for RLS)

        Returns:
            World rule with book IDs

        Raises:
            ValueError: If rule not found or access denied
        """
        try:
            # Get rule with trilogy info for RLS check
            rule_result = self.supabase.table('world_rules').select(
                '*, trilogy_projects!inner(user_id)'
            ).eq('id', rule_id).execute()

            if not rule_result.data:
                raise ValueError(f"Rule {rule_id} not found")

            rule = rule_result.data[0]

            # Check user access
            if rule['trilogy_projects']['user_id'] != user_id:
                raise ValueError("Access denied to rule")

            # Get book associations
            books_result = self.supabase.table('world_rule_books').select('book_id').eq('world_rule_id', rule_id).execute()

            book_ids = [b['book_id'] for b in books_result.data]

            # Build response
            return WorldRuleResponse(
                id=rule['id'],
                trilogy_id=rule['trilogy_id'],
                title=rule['title'],
                description=rule['description'],
                category=rule['category'],
                created_at=rule['created_at'],
                updated_at=rule['updated_at'],
                times_flagged=rule.get('times_flagged', 0),
                times_true_violation=rule.get('times_true_violation', 0),
                times_false_positive=rule.get('times_false_positive', 0),
                times_intentional_break=rule.get('times_intentional_break', 0),
                times_checker_error=rule.get('times_checker_error', 0),
                accuracy_rate=rule.get('accuracy_rate', 1.0),
                book_ids=book_ids
            )

        except ValueError as e:
            logger.error(f"Error getting rule {rule_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting rule {rule_id}: {e}")
            raise Exception(f"Failed to retrieve rule: {str(e)}")

    async def list_rules(
        self,
        trilogy_id: str,
        user_id: str,
        category: Optional[str] = None,
        book_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> WorldRuleListResponse:
        """
        List world rules for a trilogy with optional filtering.

        Args:
            trilogy_id: Trilogy to filter by
            user_id: User requesting rules (for RLS)
            category: Optional category filter
            book_id: Optional book filter (rules that apply to this book)
            page: Page number (1-indexed)
            page_size: Number of rules per page

        Returns:
            Paginated list of world rules
        """
        try:
            # Verify trilogy access
            trilogy_result = self.supabase.table('trilogy_projects').select('id, user_id').eq('id', trilogy_id).execute()

            if not trilogy_result.data:
                raise ValueError(f"Trilogy {trilogy_id} not found")

            if trilogy_result.data[0]['user_id'] != user_id:
                raise ValueError("Access denied to trilogy")

            # Build query
            query = self.supabase.table('world_rules').select('*', count='exact').eq('trilogy_id', trilogy_id)

            if category:
                query = query.eq('category', category)

            # Handle book_id filtering via JOIN
            if book_id:
                # Get rule IDs that apply to this book
                book_rules = self.supabase.table('world_rule_books').select('world_rule_id').eq('book_id', book_id).execute()
                rule_ids = [br['world_rule_id'] for br in book_rules.data]

                if not rule_ids:
                    # No rules for this book
                    return WorldRuleListResponse(
                        rules=[],
                        total=0,
                        page=page,
                        page_size=page_size,
                        total_pages=0
                    )

                query = query.in_('id', rule_ids)

            # Pagination
            offset = (page - 1) * page_size
            query = query.order('category').order('title').range(offset, offset + page_size - 1)

            result = query.execute()

            # Get book associations for each rule
            rules_with_books = []
            for rule in result.data:
                books_result = self.supabase.table('world_rule_books').select('book_id').eq('world_rule_id', rule['id']).execute()
                book_ids = [b['book_id'] for b in books_result.data]

                rules_with_books.append(WorldRuleResponse(
                    id=rule['id'],
                    trilogy_id=rule['trilogy_id'],
                    title=rule['title'],
                    description=rule['description'],
                    category=rule['category'],
                    created_at=rule['created_at'],
                    updated_at=rule['updated_at'],
                    times_flagged=rule.get('times_flagged', 0),
                    times_true_violation=rule.get('times_true_violation', 0),
                    times_false_positive=rule.get('times_false_positive', 0),
                    times_intentional_break=rule.get('times_intentional_break', 0),
                    times_checker_error=rule.get('times_checker_error', 0),
                    accuracy_rate=rule.get('accuracy_rate', 1.0),
                    book_ids=book_ids
                ))

            total = result.count if result.count is not None else len(result.data)
            total_pages = (total + page_size - 1) // page_size

            return WorldRuleListResponse(
                rules=rules_with_books,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )

        except ValueError as e:
            logger.error(f"Validation error listing rules: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing rules: {e}")
            raise Exception(f"Failed to list rules: {str(e)}")

    async def update_rule(
        self,
        rule_id: str,
        update_data: WorldRuleUpdate,
        user_id: str
    ) -> WorldRuleResponse:
        """
        Update an existing world rule and optionally its book associations.

        Args:
            rule_id: Rule to update
            update_data: Fields to update
            user_id: User updating the rule (for RLS)

        Returns:
            Updated rule

        Raises:
            ValueError: If rule not found or validation fails
        """
        try:
            # Verify rule exists and user has access
            existing_rule = await self.get_rule_by_id(rule_id, user_id)

            # Build update dict (only include fields that were provided)
            update_dict: Dict[str, Any] = {'updated_at': datetime.utcnow().isoformat()}

            if update_data.title is not None:
                update_dict['title'] = update_data.title
            if update_data.description is not None:
                update_dict['description'] = update_data.description
            if update_data.category is not None:
                update_dict['category'] = update_data.category

            # Update rule if there are changes
            if len(update_dict) > 1:  # More than just updated_at
                result = self.supabase.table('world_rules').update(update_dict).eq('id', rule_id).execute()

                if not result.data:
                    raise Exception("Failed to update rule")

                logger.info(f"Updated rule {rule_id}")

            # Update book associations if provided
            if update_data.book_ids is not None:
                # Verify books exist and belong to trilogy
                books_result = self.supabase.table('books').select('id, trilogy_id').in_('id', update_data.book_ids).execute()

                if len(books_result.data) != len(update_data.book_ids):
                    found_ids = [b['id'] for b in books_result.data]
                    missing_ids = set(update_data.book_ids) - set(found_ids)
                    raise ValueError(f"Books not found: {missing_ids}")

                for book in books_result.data:
                    if book['trilogy_id'] != existing_rule.trilogy_id:
                        raise ValueError(f"Book {book['id']} does not belong to trilogy")

                # Delete existing associations
                self.supabase.table('world_rule_books').delete().eq('world_rule_id', rule_id).execute()

                # Create new associations
                if update_data.book_ids:
                    book_associations = [
                        {'world_rule_id': rule_id, 'book_id': book_id}
                        for book_id in update_data.book_ids
                    ]
                    self.supabase.table('world_rule_books').insert(book_associations).execute()
                    logger.info(f"Updated book associations for rule {rule_id}")

            # Return updated rule
            return await self.get_rule_by_id(rule_id, user_id)

        except ValueError as e:
            logger.error(f"Validation error updating rule {rule_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error updating rule {rule_id}: {e}")
            raise Exception(f"Failed to update rule: {str(e)}")

    async def delete_rule(
        self,
        rule_id: str,
        user_id: str
    ) -> Dict[str, str]:
        """
        Delete a world rule (CASCADE deletes book associations).

        Args:
            rule_id: Rule to delete
            user_id: User deleting the rule (for RLS)

        Returns:
            Success message

        Raises:
            ValueError: If rule not found or access denied
        """
        try:
            # Verify rule exists and user has access
            await self.get_rule_by_id(rule_id, user_id)

            # Delete rule (CASCADE will handle world_rule_books)
            result = self.supabase.table('world_rules').delete().eq('id', rule_id).execute()

            if not result.data:
                raise Exception("Failed to delete rule")

            logger.info(f"Deleted rule {rule_id}")

            return {"status": "success", "message": f"Rule {rule_id} deleted"}

        except ValueError as e:
            logger.error(f"Error deleting rule {rule_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting rule {rule_id}: {e}")
            raise Exception(f"Failed to delete rule: {str(e)}")

    async def _delete_rule_by_id(self, rule_id: str) -> None:
        """Internal method to delete a rule without RLS checks (for rollback)."""
        self.supabase.table('world_rules').delete().eq('id', rule_id).execute()

    async def get_categories(
        self,
        trilogy_id: str,
        user_id: str
    ) -> CategoryListResponse:
        """
        Get all unique categories used in a trilogy's rules.

        Args:
            trilogy_id: Trilogy to get categories for
            user_id: User requesting categories (for RLS)

        Returns:
            List of unique category names
        """
        try:
            # Verify trilogy access
            trilogy_result = self.supabase.table('trilogy_projects').select('id, user_id').eq('id', trilogy_id).execute()

            if not trilogy_result.data:
                raise ValueError(f"Trilogy {trilogy_id} not found")

            if trilogy_result.data[0]['user_id'] != user_id:
                raise ValueError("Access denied to trilogy")

            # Get distinct categories
            result = self.supabase.table('world_rules').select('category').eq('trilogy_id', trilogy_id).execute()

            categories = sorted(set(rule['category'] for rule in result.data))

            return CategoryListResponse(categories=categories)

        except ValueError as e:
            logger.error(f"Error getting categories: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting categories: {e}")
            raise Exception(f"Failed to get categories: {str(e)}")

    async def get_rules_for_book(
        self,
        book_id: str,
        user_id: str,
        category: Optional[str] = None
    ) -> List[WorldRuleResponse]:
        """
        Get all rules that apply to a specific book.

        Args:
            book_id: Book to get rules for
            user_id: User requesting rules (for RLS)
            category: Optional category filter

        Returns:
            List of rules applicable to the book
        """
        try:
            # Verify book exists and get trilogy_id
            book_result = self.supabase.table('books').select('id, trilogy_id, trilogy_projects!inner(user_id)').eq('id', book_id).execute()

            if not book_result.data:
                raise ValueError(f"Book {book_id} not found")

            book = book_result.data[0]

            if book['trilogy_projects']['user_id'] != user_id:
                raise ValueError("Access denied to book")

            # Get rule IDs for this book
            book_rules = self.supabase.table('world_rule_books').select('world_rule_id').eq('book_id', book_id).execute()
            rule_ids = [br['world_rule_id'] for br in book_rules.data]

            if not rule_ids:
                return []

            # Get full rules
            query = self.supabase.table('world_rules').select('*').in_('id', rule_ids)

            if category:
                query = query.eq('category', category)

            result = query.order('category').order('title').execute()

            # Add book associations
            rules = []
            for rule in result.data:
                books_result = self.supabase.table('world_rule_books').select('book_id').eq('world_rule_id', rule['id']).execute()
                book_ids = [b['book_id'] for b in books_result.data]

                rules.append(WorldRuleResponse(
                    id=rule['id'],
                    trilogy_id=rule['trilogy_id'],
                    title=rule['title'],
                    description=rule['description'],
                    category=rule['category'],
                    created_at=rule['created_at'],
                    updated_at=rule['updated_at'],
                    times_flagged=rule.get('times_flagged', 0),
                    times_true_violation=rule.get('times_true_violation', 0),
                    times_false_positive=rule.get('times_false_positive', 0),
                    times_intentional_break=rule.get('times_intentional_break', 0),
                    times_checker_error=rule.get('times_checker_error', 0),
                    accuracy_rate=rule.get('accuracy_rate', 1.0),
                    book_ids=book_ids
                ))

            return rules

        except ValueError as e:
            logger.error(f"Error getting rules for book {book_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting rules for book {book_id}: {e}")
            raise Exception(f"Failed to get rules for book: {str(e)}")
