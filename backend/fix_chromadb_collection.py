"""
Script to diagnose and fix ChromaDB collection issues.
This script can repair or recreate the collection if needed.
"""
import logging
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from rag.vector_store import vector_store
from config import settings
import chromadb
from chromadb.config import Settings as ChromaSettings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def diagnose_collection():
    """Diagnose the ChromaDB collection."""
    logger.info("=" * 70)
    logger.info("DEBUG: ========== CHROMADB COLLECTION DIAGNOSIS ==========")
    logger.info("=" * 70)
    
    try:
        # Try to get collection
        logger.info("DEBUG: Attempting to get collection...")
        collection = vector_store.client.get_collection(name=vector_store.collection_name)
        logger.info("DEBUG: ✅ Collection retrieved successfully")
        
        # Try to peek
        try:
            sample = collection.peek(limit=1)
            logger.info("DEBUG: ✅ Collection peek successful")
            logger.info(f"DEBUG: Sample keys: {sample.keys() if isinstance(sample, dict) else 'Not a dict'}")
            return True, "Collection is accessible"
        except KeyError as ke:
            if "'_type'" in str(ke) or "_type" in str(ke):
                logger.error(f"DEBUG: ❌ Collection has '_type' error: {ke}")
                return False, f"Collection structure error: {ke}"
            else:
                raise
    except KeyError as ke:
        if "'_type'" in str(ke) or "_type" in str(ke):
            logger.error(f"DEBUG: ❌ Cannot access collection due to '_type' error: {ke}")
            return False, f"Collection access error: {ke}"
        else:
            logger.error(f"DEBUG: ❌ Cannot access collection: {ke}")
            return False, f"Collection access error: {ke}"
    except Exception as e:
        error_str = str(e)
        # Check if collection doesn't exist (this is OK, we can create it)
        if "does not exist" in error_str or "NotFoundError" in error_str:
            logger.info(f"DEBUG: ℹ️ Collection does not exist: {error_str}")
            return False, "Collection does not exist (will be created)"
        logger.error(f"DEBUG: ❌ Error diagnosing collection: {e}")
        import traceback
        logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")
        return False, f"Error: {str(e)}"


def try_direct_access():
    """Try to access collection directly using ChromaDB client."""
    logger.info("DEBUG: Attempting direct ChromaDB access...")
    try:
        client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        # List all collections
        collections = client.list_collections()
        logger.info(f"DEBUG: Found {len(collections)} collections")
        for col in collections:
            logger.info(f"DEBUG: - Collection: {col.name}")
        
        # Try to get our collection
        try:
            collection = client.get_collection(name=vector_store.collection_name)
            logger.info("DEBUG: ✅ Direct access successful")
            
            # Try count
            try:
                count = collection.count()
                logger.info(f"DEBUG: ✅ Collection count: {count}")
                return True, count
            except Exception as count_error:
                logger.warning(f"DEBUG: ⚠️ Count failed: {count_error}")
                # Try sample
                try:
                    sample = collection.get(limit=1)
                    if sample and "ids" in sample:
                        logger.info(f"DEBUG: ✅ Sample has {len(sample['ids'])} IDs")
                        return True, "Sample accessible"
                except Exception as sample_error:
                    logger.error(f"DEBUG: ❌ Sample failed: {sample_error}")
                    return False, str(sample_error)
        except KeyError as ke:
            if "'_type'" in str(ke) or "_type" in str(ke):
                logger.error(f"DEBUG: ❌ '_type' error in direct access: {ke}")
                return False, f"'_type' error: {ke}"
            else:
                raise
    except Exception as e:
        logger.error(f"DEBUG: ❌ Direct access failed: {e}")
        import traceback
        logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")
        return False, str(e)


def fix_collection():
    """
    Try to fix the collection by recreating it or resetting it.
    
    Based on ChromaDB documentation, the best approach is to:
    1. Delete the corrupted collection
    2. Create a new collection with the same name
    3. Re-index the documents
    
    If deletion fails due to '_type' error, we can try to reset the entire database.
    """
    logger.info("=" * 70)
    logger.info("DEBUG: ========== ATTEMPTING TO FIX/CREATE COLLECTION ==========")
    logger.info("=" * 70)
    
    try:
        # Use the existing client from vector_store to avoid conflicts
        client = vector_store.client
        
        # First, try to use reset() if the collection is completely corrupted
        # This is safer than trying to delete individual collections
        logger.info("DEBUG: Checking if we can access the collection to delete it...")
        can_delete = False
        try:
            # Try to get the collection to see if it's accessible
            test_collection = client.get_collection(name=vector_store.collection_name)
            can_delete = True
            logger.info("DEBUG: ✅ Collection is accessible, can delete normally")
        except (KeyError, Exception) as get_error:
            error_str = str(get_error)
            if "'_type'" in error_str or "_type" in error_str or "does not exist" in error_str:
                logger.warning(f"DEBUG: ⚠️ Cannot access collection normally: {error_str}")
                can_delete = False
            else:
                raise
        
        # Try to delete and recreate the collection
        logger.info("DEBUG: Attempting to delete corrupted collection...")
        deleted = False
        try:
            client.delete_collection(name=vector_store.collection_name)
            logger.info("DEBUG: ✅ Collection deleted via API")
            deleted = True
        except KeyError as ke:
            if "'_type'" in str(ke) or "_type" in str(ke):
                logger.warning(f"DEBUG: ⚠️ Cannot delete via API due to '_type' error: {ke}")
                logger.info("DEBUG: Attempting to delete collection files directly...")
                # Try to delete the collection directory directly
                import shutil
                collection_path = os.path.join(settings.chroma_persist_directory, "chroma.sqlite3")
                if os.path.exists(collection_path):
                    # Backup the database file
                    backup_path = collection_path + ".backup"
                    try:
                        shutil.copy2(collection_path, backup_path)
                        logger.info(f"DEBUG: ✅ Database backed up to {backup_path}")
                    except Exception as backup_error:
                        logger.warning(f"DEBUG: ⚠️ Could not backup database: {backup_error}")
                    
                    # Try to reset the client (this may help)
                    try:
                        # Close the client and try to reset
                        import sqlite3
                        # Connect to the SQLite database and delete the collection entry
                        db_path = os.path.join(settings.chroma_persist_directory, "chroma.sqlite3")
                        if os.path.exists(db_path):
                            conn = sqlite3.connect(db_path)
                            cursor = conn.cursor()
                            # Try to delete the collection from the collections table
                            try:
                                cursor.execute("DELETE FROM collections WHERE name = ?", (vector_store.collection_name,))
                                conn.commit()
                                logger.info("DEBUG: ✅ Collection entry deleted from database")
                                deleted = True
                            except Exception as sql_error:
                                logger.warning(f"DEBUG: ⚠️ Could not delete from SQL: {sql_error}")
                            finally:
                                conn.close()
                    except Exception as reset_error:
                        logger.warning(f"DEBUG: ⚠️ Could not reset via SQL: {reset_error}")
            else:
                logger.warning(f"DEBUG: ⚠️ Could not delete collection: {delete_error}")
        except Exception as delete_error:
            logger.warning(f"DEBUG: ⚠️ Could not delete collection (may not exist): {delete_error}")
        
        # If deletion failed, try to use ChromaDB's reset() method
        # This is the recommended approach according to ChromaDB documentation
        if not deleted:
            logger.warning("DEBUG: ⚠️ Standard deletion failed, attempting ChromaDB reset()...")
            logger.info("DEBUG: According to ChromaDB docs, reset() is the safest way to clear corrupted collections")
            response = input("   Standard deletion failed. Use ChromaDB reset() to clear all collections? (yes/no): ")
            if response.lower() in ['yes', 'y']:
                try:
                    # Backup the database directory first
                    import shutil
                    db_path = settings.chroma_persist_directory
                    if os.path.exists(db_path):
                        backup_path = db_path + ".backup"
                        try:
                            shutil.copytree(db_path, backup_path, dirs_exist_ok=True)
                            logger.info(f"DEBUG: ✅ Database backed up to {backup_path}")
                        except Exception as backup_error:
                            logger.warning(f"DEBUG: ⚠️ Could not backup database: {backup_error}")
                    
                    # Use ChromaDB's reset() method (recommended by documentation)
                    logger.info("DEBUG: Calling client.reset() to clear all collections...")
                    reset_result = client.reset()
                    if reset_result:
                        logger.info("DEBUG: ✅ Database reset successful")
                        deleted = True
                    else:
                        logger.warning("DEBUG: ⚠️ reset() returned False, trying manual deletion...")
                        # Fallback to manual deletion
                        if os.path.exists(db_path):
                            try:
                                shutil.rmtree(db_path)
                                logger.info("DEBUG: ✅ Database directory deleted manually")
                                os.makedirs(db_path, exist_ok=True)
                                logger.info("DEBUG: ✅ Database directory recreated")
                                deleted = True
                            except Exception as reset_error:
                                logger.error(f"DEBUG: ❌ Could not reset database manually: {reset_error}")
                                return False, f"Could not reset database: {reset_error}"
                        else:
                            logger.info("DEBUG: Database directory does not exist, will be created")
                            deleted = True
                except Exception as reset_error:
                    logger.error(f"DEBUG: ❌ Error during reset(): {reset_error}")
                    import traceback
                    logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")
                    # Try manual deletion as fallback
                    try:
                        import shutil
                        db_path = settings.chroma_persist_directory
                        if os.path.exists(db_path):
                            backup_path = db_path + ".backup"
                            try:
                                shutil.copytree(db_path, backup_path, dirs_exist_ok=True)
                                logger.info(f"DEBUG: ✅ Database backed up to {backup_path}")
                            except Exception:
                                pass
                            shutil.rmtree(db_path)
                            os.makedirs(db_path, exist_ok=True)
                            logger.info("DEBUG: ✅ Database reset via manual deletion")
                            deleted = True
                        else:
                            deleted = True
                    except Exception as manual_error:
                        logger.error(f"DEBUG: ❌ Manual reset also failed: {manual_error}")
                        return False, f"Could not reset database: {reset_error}"
            else:
                logger.info("DEBUG: Database reset cancelled")
                return False, "Deletion cancelled by user"
        
        # Recreate collection using get_or_create_collection (recommended by ChromaDB docs)
        # This ensures we get the collection even if it was partially created
        logger.info("DEBUG: Creating new collection using get_or_create_collection()...")
        try:
            # Use get_or_create_collection to be safe (handles edge cases better)
            new_collection = client.get_or_create_collection(
                name=vector_store.collection_name,
                metadata={"description": "ESILV documentation collection"}
            )
            logger.info("DEBUG: ✅ New collection created/retrieved")
            
            # Verify the collection is accessible
            try:
                test_peek = new_collection.peek(limit=1)
                logger.info("DEBUG: ✅ Collection is accessible (peek works)")
            except Exception as peek_error:
                logger.warning(f"DEBUG: ⚠️ Collection created but peek failed: {peek_error}")
        except Exception as create_error:
            logger.error(f"DEBUG: ❌ Could not create collection: {create_error}")
            import traceback
            logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")
            return False, f"Could not create collection: {create_error}"
        
        # Reset vector store to force re-initialization
        vector_store._vectorstore = None
        logger.info("DEBUG: ✅ Vector store reset")
        
        # Test that the vector store can now access the collection
        try:
            test_vs = vector_store.vectorstore
            logger.info("DEBUG: ✅ Vector store can access the new collection")
        except Exception as vs_error:
            logger.warning(f"DEBUG: ⚠️ Vector store access test failed: {vs_error}")
            # This is not critical, the collection exists and can be used
        
        return True, "Collection recreated successfully"
    except Exception as e:
        logger.error(f"DEBUG: ❌ Error fixing collection: {e}")
        import traceback
        logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")
        return False, str(e)


def main():
    """Main function."""
    logger.info("=" * 70)
    logger.info("CHROMADB COLLECTION DIAGNOSIS AND REPAIR TOOL")
    logger.info("=" * 70)
    
    # Step 1: Diagnose
    logger.info("\n1. DIAGNOSING COLLECTION...")
    accessible, message = diagnose_collection()
    logger.info(f"   Result: {message}")
    
    # Check if collection needs to be created or fixed
    needs_fix = not accessible
    needs_create = "does not exist" in message or "NotFoundError" in message
    
    if needs_fix:
        # Step 2: Try direct access (skip if collection doesn't exist)
        if not needs_create:
            logger.info("\n2. TRYING DIRECT ACCESS...")
            direct_ok, direct_msg = try_direct_access()
            logger.info(f"   Result: {direct_msg}")
            needs_fix = not direct_ok or "'_type'" in str(direct_msg) or "_type" in str(direct_msg)
        else:
            logger.info("\n2. SKIPPING DIRECT ACCESS (collection does not exist)")
            direct_ok = False
        
        if needs_fix or needs_create:
            # Step 3: Fix or create collection
            if needs_create:
                logger.info("\n3. CREATING NEW COLLECTION...")
                logger.info("   The collection does not exist. Creating a new one.")
            else:
                logger.info("\n3. ATTEMPTING TO FIX COLLECTION...")
                logger.warning("   WARNING: This will DELETE the current collection and create a new one!")
                logger.warning("   All indexed documents will be lost and need to be re-indexed.")
                logger.warning("   A backup will be created before deletion.")
            
            if needs_create:
                # Auto-create if collection doesn't exist
                fixed, fix_msg = fix_collection()
                logger.info(f"   Result: {fix_msg}")
                if fixed:
                    logger.info("\n✅ Collection created! You will need to index your documents.")
                    logger.info("   Run: python scrape_esilv.py --priority")
                else:
                    logger.error("\n❌ Failed to create collection. Manual intervention may be required.")
            else:
                response = input("\n   Do you want to proceed? (yes/no): ")
                if response.lower() in ['yes', 'y']:
                    fixed, fix_msg = fix_collection()
                    logger.info(f"   Result: {fix_msg}")
                    if fixed:
                        logger.info("\n✅ Collection fixed! You will need to re-index your documents.")
                        logger.info("   Run: python scrape_esilv.py --priority")
                    else:
                        logger.error("\n❌ Failed to fix collection. Manual intervention may be required.")
                        logger.error("   You may need to manually delete the ChromaDB directory and restart.")
                else:
                    logger.info("   Operation cancelled.")
        else:
            logger.info("\n✅ Collection is accessible via direct method. The issue may be in the LangChain wrapper.")
    else:
        logger.info("\n✅ Collection is healthy and accessible!")
    
    logger.info("=" * 70)


if __name__ == "__main__":
    main()

