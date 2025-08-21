"""
Kafka client imports for backward compatibility.

This module re-exports classes from separate files for backward compatibility.
For new code, import directly from the specific modules:
- from .kafka_producer import KafkaProducer
- from .kafka_consumer import KafkaConsumer
- from .kafka_manager import KafkaManager
"""

# Import classes from separate files for backward compatibility
from .kafka_producer import KafkaProducer
from .kafka_consumer import KafkaConsumer
from .kafka_manager import KafkaManager

__all__ = ['KafkaProducer', 'KafkaConsumer', 'KafkaManager'] 