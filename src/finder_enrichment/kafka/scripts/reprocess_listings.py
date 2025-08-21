import json
import os
from listings_db_api_client.listings_db_api_client import ListingsDBAPIClient
from ..kafka_producer import KafkaProducer
from ...logger_config import setup_logger

# Configure logging
logger = setup_logger(__name__)

# Define the Kafka topic
PROPERTY_DISCOVERED_TOPIC = "finder.harvester.property.discovered"

def reprocess_all_listings():
    """
    Fetches all listings from the database and sends a message for each
    to the PROPERTY_DISCOVERED Kafka topic.
    """
    db_api_client = None
    kafka_producer = None
    try:
        # Initialize the database API client
        db_api_client = ListingsDBAPIClient(api_key=os.getenv("LISTINGS_DB_API_KEY"), base_url=os.getenv("LISTINGS_DB_BASE_URL"))
        logger.info("Successfully connected to the listings database API.")

        # Initialize the Kafka producer
        kafka_producer = KafkaProducer()
        logger.info("Successfully initialized Kafka producer.")

        # Fetch all listings using pagination
        logger.info("Fetching all listings from the database...")
        all_listings = []
        skip = 0
        limit = 100  # Process 100 listings at a time

        while True:
            response = db_api_client.get_listings(skip=skip, limit=limit)

            if response.errors:
                logger.error(f"Error fetching listings: {response.errors}")
                break

            fetched_listings = response.results
            if not fetched_listings:
                # No more listings to fetch
                break
            
            all_listings.extend(fetched_listings)
            skip += limit

        if not all_listings:
            logger.info("No listings found in the database.")
            return

        logger.info(f"Found {len(all_listings)} listings to reprocess.")

        # Send a message for each listing
        for listing in all_listings:
            listing_id = listing.id
            message = {"listing_id": listing_id}
            
            logger.info(f"Sending message for listing ID: {listing_id} to topic '{PROPERTY_DISCOVERED_TOPIC}'")
            kafka_producer.produce_message(
                topic=PROPERTY_DISCOVERED_TOPIC,
                message=message,
                key=str(listing_id)
            )

        # Wait for all messages to be delivered
        kafka_producer.flush()
        logger.info("All messages have been sent successfully.")

    except Exception as e:
        logger.error(f"An error occurred during reprocessing: {e}", exc_info=True)
    finally:
        # Clean up connections
        if db_api_client:
            db_api_client.close()
            logger.info("Database API client closed.")
        if kafka_producer:
            kafka_producer.close()
            logger.info("Kafka producer closed.")

if __name__ == "__main__":
    reprocess_all_listings() 