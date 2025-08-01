from src.ai_coach.rag_chain import create_rag_chain
from src.config.model_constants import LLM_MODEL
import os
from datetime import datetime

# Tenant-scoped conversation storage for Phase 2 (preparing for Phase 5 isolation)
_rag_chains = {}

def get_rag_chain(conversation_id=None, tenant_id=None, user_email=None):
    """
    Get or create the RAG chain for a specific conversation with tenant+user scoping.
    Model is now standardized to Llama 3.3 - no model selection needed.
    """
    global _rag_chains
    
    # VALIDATION: For tenant users, user_email is mandatory for isolation
    if tenant_id and not user_email:
        raise ValueError(
            f"user_email is required for tenant operations (tenant_id: {tenant_id}). "
            f"This ensures complete conversation isolation between users."
        )
    
    # Use default conversation if none provided
    if not conversation_id:
        conversation_id = "default"
    
    # Create session key with CONSISTENT format (no fallbacks to old format)
    if tenant_id and user_email:
        # Full isolation: tenant + user + conversation
        chain_key = f"tenant_{tenant_id}_user_{user_email}_{conversation_id}"
    elif not tenant_id:  # Super admin only
        chain_key = f"global_{conversation_id}"
    else:
        # This should never happen due to validation above
        raise ValueError("Invalid session parameters: tenant_id provided without user_email")
    
    # Create chain if it doesn't exist
    if chain_key not in _rag_chains:
        chroma_db_path = os.path.join(os.path.dirname(__file__), "../../chroma_db")
        
        # Always use standardized Llama 3.3 model (no model selection)
        _rag_chains[chain_key] = create_rag_chain(
            persist_directory=chroma_db_path, 
            model_id=LLM_MODEL  # Force Llama 3.3 70B
        )
        
        print(f"✅ Created new RAG chain: {chain_key} using {LLM_MODEL}")
    
    return _rag_chains[chain_key]

def clear_conversation_memory(conversation_id, tenant_id=None, user_email=None):
    """
    Clear the memory for a specific conversation with tenant+user scoping.
    """
    global _rag_chains
    
    # VALIDATION: Apply same validation as get_rag_chain
    if tenant_id and not user_email:
        raise ValueError(
            f"user_email is required for tenant operations (tenant_id: {tenant_id}). "
            f"Cannot clear conversation without proper user isolation."
        )
    
    # Create the same key format as get_rag_chain
    if tenant_id and user_email:
        # Full isolation: tenant + user + conversation
        chain_key = f"tenant_{tenant_id}_user_{user_email}_{conversation_id}"
    elif not tenant_id:  # Super admin only
        chain_key = f"global_{conversation_id}"
    else:
        # This should never happen due to validation above
        raise ValueError("Invalid session parameters: tenant_id provided without user_email")
    
    # Remove the specific chain
    if chain_key in _rag_chains:
        del _rag_chains[chain_key]
        print(f"✅ Cleared memory for conversation chain: {chain_key}")
        return True
    else:
        print(f"⚠️  No conversation chain found for: {chain_key}")
        return False

def get_conversation_history(conversation_id: str, tenant_id=None, user_email=None):
    """
    Get conversation history for a specific conversation with tenant+user scoping.
    """
    try:
        # FIX: Pass all three parameters to maintain session key consistency
        chain = get_rag_chain(conversation_id, tenant_id, user_email)
        
        # Extract conversation history from the chain's memory
        if hasattr(chain, 'memory') and hasattr(chain.memory, 'chat_memory'):
            messages = chain.memory.chat_memory.messages
            
            # Convert to a more readable format
            history = []
            for i in range(0, len(messages), 2):
                if i + 1 < len(messages):
                    history.append({
                        "question": messages[i].content,
                        "answer": messages[i + 1].content,
                        "timestamp": getattr(messages[i], 'timestamp', None)
                    })
            
            return history
        
        return []
        
    except Exception as e:
        print(f"❌ Error getting conversation history: {e}")
        return []

async def ask_ai_coach(question: str, conversation_id: str = None, model_id: str = None, tenant_id: str = None, user_email: str = None):
    """
    Ask a question to the AI Coach with standardized model and tenant+user scoping.
    
    Args:
        question: The user's question
        conversation_id: Conversation identifier for memory
        model_id: IGNORED - always uses standardized Llama 3.3
        tenant_id: Tenant identifier for conversation isolation
        user_email: User identifier for complete isolation within tenant
    """
    try:
        # Ensure we have a conversation ID
        if not conversation_id:
            conversation_id = "default"
        
        # Get RAG chain with tenant+user scoping (model is standardized)
        chain = get_rag_chain(conversation_id, tenant_id, user_email)
        
        # Process the question
        result = chain({"question": question})
        
        return {
            "answer": result["answer"],
            "conversation_id": conversation_id,
            "model_used": LLM_MODEL,  # Always Llama 3.3
            "tenant_id": tenant_id,
            "user_email": user_email,  # Add user tracking
            "sources": result.get("source_documents", [])
        }
        
    except Exception as e:
        print(f"Error in AI Coach: {e}")
        return {
            "error": "An error occurred while processing your question.",
            "details": str(e),
            "model_used": LLM_MODEL,
            "conversation_id": conversation_id,
            "tenant_id": tenant_id,
            "user_email": user_email
        }

def clear_all_conversations(tenant_id=None):
    """
    Clear all conversations for a specific tenant (or all global conversations).
    Useful for testing or admin operations.
    """
    global _rag_chains
    
    if tenant_id:
        # Clear all conversations for a specific tenant
        prefix = f"tenant_{tenant_id}_"
        keys_to_remove = [key for key in _rag_chains.keys() if key.startswith(prefix)]
    else:
        # Clear all global conversations
        keys_to_remove = [key for key in _rag_chains.keys() if key.startswith("global_")]
    
    for key in keys_to_remove:
        del _rag_chains[key]
    
    print(f"Cleared {len(keys_to_remove)} conversation chains for tenant: {tenant_id or 'global'}")

def get_active_conversations(requesting_tenant_id=None):
    """
    Get list of active conversations with optional tenant filtering.
    Enhanced to handle new session key format: tenant_{tenant_id}_user_{user_email}_{conversation_id}
    """
    global _rag_chains
    
    conversations = {
        "total_chains": len(_rag_chains),
        "conversations": [],
        "requesting_tenant": requesting_tenant_id
    }
    
    for chain_key in _rag_chains.keys():
        include_conversation = False
        conversation_info = None
        
        if chain_key.startswith("tenant_"):
            # Parse tenant conversation - handle both old and new formats
            parts = chain_key.split("_")
            
            if len(parts) >= 5 and parts[2] == "user":
                # NEW FORMAT: tenant_{tenant_id}_user_{user_email}_{conversation_id}
                conversation_tenant_id = parts[1]
                user_email = parts[3]
                conversation_id = "_".join(parts[4:])  # Handle conversation IDs with underscores
                
                conversation_info = {
                    "type": "tenant",
                    "tenant_id": conversation_tenant_id,
                    "user_email": user_email,
                    "conversation_id": conversation_id,
                    "chain_key": chain_key,
                    "format": "user_scoped"
                }
                
            elif len(parts) >= 3:
                # OLD FORMAT: tenant_{tenant_id}_{conversation_id} (for backwards compatibility)
                conversation_tenant_id = parts[1]
                conversation_id = "_".join(parts[2:])  # Handle conversation IDs with underscores
                
                conversation_info = {
                    "type": "tenant",
                    "tenant_id": conversation_tenant_id,
                    "user_email": None,
                    "conversation_id": conversation_id,
                    "chain_key": chain_key,
                    "format": "tenant_scoped"
                }
            
            # Check if requester can access this conversation
            if conversation_info:
                if requesting_tenant_id is None or requesting_tenant_id == conversation_info["tenant_id"]:
                    include_conversation = True
                    
        elif chain_key.startswith("global_"):
            # Parse global conversation
            conversation_id = chain_key.replace("global_", "")
            conversation_info = {
                "type": "global",
                "tenant_id": None,
                "user_email": None,
                "conversation_id": conversation_id,
                "chain_key": chain_key,
                "format": "global"
            }
            
            # Only super admin (requesting_tenant_id=None) can see global conversations
            if requesting_tenant_id is None:
                include_conversation = True
        
        if include_conversation and conversation_info:
            conversations["conversations"].append(conversation_info)
    
    conversations["total_chains"] = len(conversations["conversations"])
    return conversations