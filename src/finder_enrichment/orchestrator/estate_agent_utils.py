import os
from typing import Optional

from dotenv import load_dotenv
from finder_enrichment_db_client import FinderEnrichmentDBAPIClient
from finder_enrichment_db_contracts.schemas import AddressCreate, EstateAgentCreate, Address
from finder_enrichment.logger_config import setup_logger

logger = setup_logger(__name__)
load_dotenv()


def get_or_create_estate_agent(original_agent) -> Optional[int]:
    """
    Gets an existing estate agent from the enriched database by name,
    or creates a new one if it doesn't exist.

    Args:
        original_agent: The estate agent data from the original listing.

    Returns:
        The ID of the existing or newly created estate agent, or None if creation fails.
    """
    enriched_db_client: FinderEnrichmentDBAPIClient = FinderEnrichmentDBAPIClient(os.getenv("ENRICHMENT_DB_BASE_URL", "http://localhost:8200"), os.getenv("ENRICHMENT_DB_API_KEY"))

    agent_name = original_agent.name
    logger.info(f"Searching for existing estate agent: {agent_name}")

    all_agents = enriched_db_client.get_estate_agents(limit=10000)
    existing_agent = next((agent for agent in all_agents if agent.name == agent_name), None)

    if existing_agent:
        logger.info(f"Found existing estate agent '{existing_agent.name}' with ID {existing_agent.id}")
        return existing_agent.id
    else:
        logger.info(f"Estate agent '{agent_name}' not found. Creating a new one.")
        try:
            address_create = None
            if original_agent.address:
                address_data = original_agent.address.__dict__ if hasattr(original_agent.address, '__dict__') else original_agent.address
                valid_address_fields = AddressCreate.model_fields.keys()
                filtered_address_data = {k: v for k, v in address_data.items() if k in valid_address_fields}
                address_create = AddressCreate(**filtered_address_data)

            agent_create = EstateAgentCreate(
                name=original_agent.name,
                website=original_agent.website,
                phone=original_agent.phone,
                email=original_agent.email,
                address=address_create
            )
            new_agent = enriched_db_client.create_estate_agent(agent_create)
            logger.info(f"Successfully created new estate agent '{new_agent.name}' with ID {new_agent.id}")
            return new_agent.id
        except Exception as e:
            logger.error(f"Failed to create new estate agent '{agent_name}': {e}", exc_info=True)
            return None