#!/usr/bin/env python3
"""
Property Recommendation Application using Agent-based Architecture

This application demonstrates a two-agent system for property recommendation:
1. Customer Profiler Agent: Analyzes customer requirements and scores properties
2. Listings Curator Agent: Searches and filters property listings from CSV data

The agents negotiate to find the best property matches for a given customer profile.
"""

import os
import sys
import json
import pandas as pd
import time
from pathlib import Path
import shutil
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
from finder_enrichment_ai_client.finder_enrichment_ai_client import FinderEnrichmentGoogleAIClient
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ..logger_config import setup_logger

# Load environment variables
load_dotenv()

logger = setup_logger(__name__)


@dataclass
class PropertyRecommendation:
    """Data class for property recommendations with scoring."""
    property_id: int
    title: str
    price: float
    bedrooms: int
    bathrooms: int
    property_type: Optional[str]
    location: Optional[str]
    reasoning: str
    appropriateness_score: int
    key_features: List[str]

    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AgentInteraction:
    """Data class for tracking agent interactions."""
    agent_name: str
    action: str
    prompt: str
    response: str
    timestamp: float
    processing_time: float
    token_count_estimate: int

    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PerformanceMetrics:
    """Data class for system performance metrics."""
    total_processing_time: float
    properties_processed: int
    properties_filtered: int
    properties_curated: int
    properties_scored: int
    avg_appropriateness_score: float
    max_appropriateness_score: int
    min_appropriateness_score: int
    agent_interactions: List[AgentInteraction]
    success_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return {
            "total_processing_time": self.total_processing_time,
            "properties_processed": self.properties_processed,
            "properties_filtered": self.properties_filtered,
            "properties_curated": self.properties_curated,
            "properties_scored": self.properties_scored,
            "avg_appropriateness_score": self.avg_appropriateness_score,
            "max_appropriateness_score": self.max_appropriateness_score,
            "min_appropriateness_score": self.min_appropriateness_score,
            "success_rate": self.success_rate,
            "agent_interactions_count": len(self.agent_interactions)
        }


class AgentConfig:
    """Configuration for Google Gemini agents using lightweight HTTP client."""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_GEMINI_API_KEY not found in environment variables")
        
        # Initialize lightweight HTTP client
        self.client = FinderEnrichmentGoogleAIClient(api_key=self.api_key)
        
        # Use Gemini 1.5 Flash for fast, free responses
        self.model = "gemini-2.0-flash"
        self.temperature = 0.7
        self.max_tokens = 100000
        
    def get_client(self):
        """Get a properly configured lightweight Google AI client."""
        return self.client


class PropertyDataManager:
    """Manages loading and filtering of property data from CSV."""
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.properties_df = None
        self.load_data()
    
    def load_data(self):
        """Load property data from CSV file."""
        try:
            if not os.path.exists(self.csv_path):
                raise FileNotFoundError(f"CSV file not found: {self.csv_path}")
            
            self.properties_df = pd.read_csv(self.csv_path)
            logger.info(f"Loaded {len(self.properties_df)} properties from {self.csv_path}")
            
            # Clean data and handle missing values
            self.properties_df['price'] = pd.to_numeric(self.properties_df['price'], errors='coerce')
            self.properties_df['bedrooms'] = pd.to_numeric(self.properties_df['bedrooms'], errors='coerce')
            self.properties_df['bathrooms'] = pd.to_numeric(self.properties_df['bathrooms'], errors='coerce')
            
            # Fill NaN values for text fields
            text_columns = ['property_tags', 'description', 'title']
            for col in text_columns:
                if col in self.properties_df.columns:
                    self.properties_df[col] = self.properties_df[col].fillna('')
            
        except Exception as e:
            logger.error(f"Error loading CSV data: {e}")
            raise
    
    def get_properties_as_dict(self) -> List[Dict[str, Any]]:
        """Convert DataFrame to list of dictionaries for agent processing."""
        return self.properties_df.to_dict('records')
    
    def filter_by_budget(self, max_budget: float, min_budget: float = 0) -> pd.DataFrame:
        """Filter properties by budget range."""
        mask = (self.properties_df['price'] >= min_budget) & (self.properties_df['price'] <= max_budget)
        return self.properties_df[mask]


class CustomerProfilerAgent:
    """Agent responsible for analyzing customer requirements and scoring properties."""
    
    def __init__(self, config: AgentConfig, agent_profile_path: str):
        self.config = config
        self.client = config.get_client()
        self.agent_profile_path = agent_profile_path
        self.agent_profile = self._load_agent_profile(agent_profile_path)
        self.interactions: List[AgentInteraction] = []
        
    def _load_agent_profile(self, profile_path: str) -> str:
        """Load agent profile from markdown file."""
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading agent profile from {profile_path}: {e}")
            raise
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        return len(text.split()) * 1.3  # Rough estimate
    
    def _record_interaction(self, action: str, prompt: str, response: str, processing_time: float):
        """Record an agent interaction for analysis."""
        interaction = AgentInteraction(
            agent_name="Customer Profiler Agent",
            action=action,
            prompt=prompt,
            response=response,
            timestamp=time.time(),
            processing_time=processing_time,
            token_count_estimate=int(self._estimate_tokens(prompt + response))
        )
        self.interactions.append(interaction)
        
        # Log the interaction
        logger.info(f"🤖 Customer Profiler Agent - {action}")
        logger.info(f"⏱️  Processing time: {processing_time:.2f}s")
        logger.info(f"📊 Estimated tokens: {interaction.token_count_estimate}")
    
    def analyze_customer_profile(self, customer_profile: str) -> Dict[str, Any]:
        """Analyze customer profile and extract key requirements."""
        prompt = f"""
        {self.agent_profile}
        
        Your task is to analyze the customer profile and extract structured requirements.
        Return your analysis as JSON with the following structure:
        {{
            "critical_requirements": {{
                "max_budget": number,
                "min_bedrooms": number,
                "property_types": [list of acceptable types],
                "location_constraints": "description"
            }},
            "high_priority": {{
                "parking_required": boolean,
                "garden_required": boolean,
                "min_bathrooms": number,
                "no_chain_preferred": boolean
            }},
            "medium_priority": {{
                "council_tax_max_band": "letter",
                "tenure_preference": "freehold/leasehold/either",
                "reception_rooms": number
            }},
            "summary": "Brief summary of customer needs"
        }}
        
        Customer Profile:
        {customer_profile}
        """
        
        start_time = time.time()
        try:
            response = self.client.generate_content(
                prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            processing_time = time.time() - start_time
            
            # Parse JSON response
            content = response["text"]
            # Clean up potential markdown formatting
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            requirements = json.loads(content)
            
            # Record interaction
            sanitized_prompt = prompt.replace(
                self.agent_profile, 
                f"<Agent Profile: {Path(self.agent_profile_path).name}>"
            )
            self._record_interaction("analyze_customer_profile", sanitized_prompt, content, processing_time)
            
            logger.info("Successfully analyzed customer profile")
            return requirements
            
        except Exception as e:
            processing_time = time.time() - start_time
            sanitized_prompt = prompt.replace(
                self.agent_profile, 
                f"<Agent Profile: {Path(self.agent_profile_path).name}>"
            )
            self._record_interaction("analyze_customer_profile_ERROR", sanitized_prompt, str(e), processing_time)
            logger.error(f"Error analyzing customer profile: {e}")
            raise
    
    def score_properties(self, properties: List[Dict[str, Any]], requirements: Dict[str, Any]) -> List[PropertyRecommendation]:
        """Score and evaluate properties against customer requirements."""
        # Limit to reasonable number of properties for API call
        properties_subset = properties[:10]  # Process in batches if needed
        
        properties_to_score_json = json.dumps(properties_subset, indent=2)

        prompt = f"""
        {self.agent_profile}
        
        Score each property (0-100) based on how well it matches the customer requirements.
        For each property, provide:
        1. Appropriateness score (0-100)
        2. Detailed reasoning for the score
        3. Key matching features
        
        Return as JSON array with this structure for each property:
        {{
            "property_id": number,
            "appropriateness_score": number,
            "reasoning": "detailed explanation",
            "key_features": ["feature1", "feature2"]
        }}
        
        Customer Requirements:
        {json.dumps(requirements, indent=2)}
        
        Properties to Score:
        {properties_to_score_json}
        """
        
        start_time = time.time()
        try:
            response = self.client.generate_content(
                prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            processing_time = time.time() - start_time
            
            # Parse response and create PropertyRecommendation objects
            content = response["text"]
            # Clean up potential markdown formatting
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            scores_data = json.loads(content)
            recommendations = []
            
            for score_data in scores_data:
                # Find corresponding property
                prop_id = score_data['property_id']
                property_data = next((p for p in properties_subset if p['id'] == prop_id), None)
                
                if property_data:
                    # Ensure numeric fields are correctly handled if they are missing or NaN
                    price = property_data.get('price')
                    bedrooms = property_data.get('bedrooms')
                    bathrooms = property_data.get('bathrooms')
                    prop_type = property_data.get('property_type')
                    location = property_data.get('postcode')
                    
                    recommendation = PropertyRecommendation(
                        property_id=int(prop_id),
                        title=property_data.get('title', 'Unknown'),
                        price=float(price) if pd.notna(price) else 0.0,
                        bedrooms=int(bedrooms) if pd.notna(bedrooms) else 0,
                        bathrooms=int(bathrooms) if pd.notna(bathrooms) else 0,
                        property_type=prop_type if pd.notna(prop_type) else None,
                        location=location if pd.notna(location) else None,
                        reasoning=score_data.get('reasoning', 'No reasoning provided.'),
                        appropriateness_score=int(score_data.get('appropriateness_score', 0) or 0),
                        key_features=score_data.get('key_features', [])
                    )
                    recommendations.append(recommendation)
            
            # Sanitize prompt for logging
            sanitized_prompt = prompt.replace(
                self.agent_profile,
                f"<Agent Profile: {Path(self.agent_profile_path).name}>"
            )
            property_ids = [p.get('id', 'N/A') for p in properties_subset]
            sanitized_prompt = sanitized_prompt.replace(
                properties_to_score_json,
                f"<List of {len(properties_subset)} properties with IDs: {property_ids}>"
            )

            # Record interaction
            self._record_interaction("score_properties", sanitized_prompt, content, processing_time)
            
            logger.info(f"Scored {len(recommendations)} properties")
            return recommendations
            
        except Exception as e:
            processing_time = time.time() - start_time
            # Sanitize prompt for logging
            sanitized_prompt = prompt.replace(
                self.agent_profile,
                f"<Agent Profile: {Path(self.agent_profile_path).name}>"
            )
            property_ids = [p.get('id', 'N/A') for p in properties_subset]
            sanitized_prompt = sanitized_prompt.replace(
                json.dumps(properties_subset, indent=2),
                f"<List of {len(properties_subset)} properties with IDs: {property_ids}>"
            )
            self._record_interaction("score_properties_ERROR", sanitized_prompt, str(e), processing_time)
            logger.error(f"Error scoring properties: {e}")
            raise


class ListingsCuratorAgent:
    """Agent responsible for searching and curating property listings."""
    
    def __init__(self, config: AgentConfig, agent_profile_path: str):
        self.config = config
        self.client = config.get_client()
        self.agent_profile_path = agent_profile_path
        self.agent_profile = self._load_agent_profile(agent_profile_path)
        self.interactions: List[AgentInteraction] = []
    
    def _load_agent_profile(self, profile_path: str) -> str:
        """Load agent profile from markdown file."""
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading agent profile from {profile_path}: {e}")
            raise
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        return len(text.split()) * 1.3  # Rough estimate
    
    def _record_interaction(self, action: str, prompt: str, response: str, processing_time: float):
        """Record an agent interaction for analysis."""
        interaction = AgentInteraction(
            agent_name="Listings Curator Agent",
            action=action,
            prompt=prompt,
            response=response,
            timestamp=time.time(),
            processing_time=processing_time,
            token_count_estimate=int(self._estimate_tokens(prompt + response))
        )
        self.interactions.append(interaction)
        
        # Log the interaction
        logger.info(f"🏠 Listings Curator Agent - {action}")
        logger.info(f"⏱️  Processing time: {processing_time:.2f}s")
        logger.info(f"📊 Estimated tokens: {interaction.token_count_estimate}")
    
    def curate_listings(self, properties: List[Dict[str, Any]], requirements: Dict[str, Any], max_results: int = 10) -> List[Dict[str, Any]]:
        """Curate and filter listings based on customer requirements."""
        properties_to_curate_json = json.dumps(properties, indent=2)

        prompt = f"""
        {self.agent_profile}
        
        Your task is to curate the best property listings based on customer requirements.
        Apply filtering logic and select the most suitable properties.
        
        Return a JSON array of property IDs for the best matches (up to {max_results} properties).
        Focus on properties that meet critical requirements first, then high-priority preferences.
        
        Return format: {{"selected_property_ids": [id1, id2, id3, ...]}}
        
        Customer Requirements:
        {json.dumps(requirements, indent=2)}
        
        Available Properties:
        {properties_to_curate_json}
        """
        
        start_time = time.time()
        try:
            response = self.client.generate_content(
                prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            processing_time = time.time() - start_time
            
            # Parse response
            content = response["text"]
            # Clean up potential markdown formatting
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content)
            selected_ids = result['selected_property_ids']
            
            # Filter properties to return only selected ones
            curated_properties = [p for p in properties if p['id'] in selected_ids]
            
            # Sanitize prompt for logging
            sanitized_prompt = prompt.replace(
                self.agent_profile,
                f"<Agent Profile: {Path(self.agent_profile_path).name}>"
            )
            property_ids = [p.get('id', 'N/A') for p in properties]
            sanitized_prompt = sanitized_prompt.replace(
                properties_to_curate_json,
                f"<List of {len(properties)} properties with IDs: {property_ids}>"
            )
            
            # Record interaction
            self._record_interaction("curate_listings", sanitized_prompt, content, processing_time)
            
            logger.info(f"Curated {len(curated_properties)} properties from {len(properties)} available")
            return curated_properties
            
        except Exception as e:
            processing_time = time.time() - start_time
            # Sanitize prompt for logging
            sanitized_prompt = prompt.replace(
                self.agent_profile,
                f"<Agent Profile: {Path(self.agent_profile_path).name}>"
            )
            property_ids = [p.get('id', 'N/A') for p in properties]
            sanitized_prompt = sanitized_prompt.replace(
                json.dumps(properties, indent=2),
                f"<List of {len(properties)} properties with IDs: {property_ids}>"
            )
            self._record_interaction("curate_listings_ERROR", sanitized_prompt, str(e), processing_time)
            logger.error(f"Error curating listings: {e}")
            raise


class PropertyRecommendationApp:
    """Main application orchestrator."""
    
    def __init__(self, csv_path: str, customer_profile_path: str):
        self.config = AgentConfig()
        self.data_manager = PropertyDataManager(csv_path)
        
        # Get path to agent profiles
        app_dir = Path(__file__).parent
        self.customer_profiler_agent_profile_path = app_dir / "customer_profiler_agent.md"
        self.listings_curator_agent_profile_path = app_dir / "listings_curator_agent.md"
        
        # Initialize agents
        self.customer_profiler_agent = CustomerProfilerAgent(self.config, self.customer_profiler_agent_profile_path)
        self.listings_curator_agent = ListingsCuratorAgent(self.config, self.listings_curator_agent_profile_path)
        
        # This will now be a directory path
        self.customer_profile_path = customer_profile_path 
        self.current_customer_profile_path = None # Will be set for each profile run

        # Create a single timestamped directory for this entire run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_output_dir = Path(f"testing/property_recommendations/{timestamp}")
        self.run_output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📂 Created output directory for this run: {self.run_output_dir}")

    def _load_customer_profile(self, profile_path: str) -> str:
        """Load customer profile from markdown file."""
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading customer profile from {profile_path}: {e}")
            raise
    
    def generate_recommendations(self, customer_profile_path: Path) -> tuple[List[PropertyRecommendation], PerformanceMetrics]:
        """
        Main application logic to generate property recommendations for a single customer profile.
        """
        self.start_time = time.time()
        self.current_customer_profile_path = customer_profile_path # Store current profile path
        
        # Load customer profile content
        customer_profile = self._load_customer_profile(customer_profile_path)
        
        # Reset interactions for each run
        self.customer_profiler_agent.interactions = []
        self.listings_curator_agent.interactions = []
        
        # Step 1: Profiler analyzes customer requirements
        logger.info("Step 1: Analyzing customer profile...")
        requirements = self.customer_profiler_agent.analyze_customer_profile(customer_profile)
        
        # Step 2: Apply basic filtering based on critical requirements
        logger.info("Step 2: Applying initial filtering...")
        all_properties = self.data_manager.get_properties_as_dict()
        
        # Filter by budget if specified
        if 'max_budget' in requirements.get('critical_requirements', {}):
            max_budget = requirements['critical_requirements']['max_budget']
            filtered_df = self.data_manager.filter_by_budget(max_budget)
            filtered_properties = filtered_df.to_dict('records')
        else:
            filtered_properties = all_properties
        
        logger.info(f"Filtered to {len(filtered_properties)} properties within budget")
        
        # Step 3: Curator curates best listings
        logger.info("Step 3: Curating listings...")
        curated_properties = self.listings_curator_agent.curate_listings(
            filtered_properties, 
            requirements, 
            max_results=10
        )
        
        # Step 4: Profiler scores final properties
        logger.info("Step 4: Scoring final properties...")
        recommendations = self.customer_profiler_agent.score_properties(curated_properties, requirements)
        
        # Sort by score (highest first)
        recommendations.sort(key=lambda x: x.appropriateness_score, reverse=True)
        
        # Calculate performance metrics
        total_time = time.time() - self.start_time
        all_interactions = self.customer_profiler_agent.interactions + self.listings_curator_agent.interactions
        
        if recommendations:
            scores = [r.appropriateness_score for r in recommendations]
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            success_rate = len([s for s in scores if s >= 70]) / len(scores) * 100
        else:
            avg_score = max_score = min_score = success_rate = 0
        
        metrics = PerformanceMetrics(
            total_processing_time=total_time,
            properties_processed=len(all_properties),
            properties_filtered=len(filtered_properties),
            properties_curated=len(curated_properties),
            properties_scored=len(recommendations),
            avg_appropriateness_score=avg_score,
            max_appropriateness_score=max_score,
            min_appropriateness_score=min_score,
            agent_interactions=all_interactions,
            success_rate=success_rate
        )
        
        logger.info(f"Generated {len(recommendations)} final recommendations")
        return recommendations, metrics
    
    def run_for_all_profiles(self):
        """Run the recommendation process for all customer profiles in the configured directory."""
        profile_dir = Path(self.customer_profile_path)
        if not profile_dir.is_dir():
            logger.error(f"Customer profile path is not a directory: {profile_dir}")
            print(f"❌ Error: Customer profile path must be a directory: {profile_dir}")
            return

        profile_files = list(profile_dir.glob("*.md"))
        if not profile_files:
            logger.warning(f"No customer profiles found in {profile_dir}")
            print(f"⚠️ No customer profiles (.md files) found in {profile_dir}")
            return
            
        logger.info(f"Found {len(profile_files)} customer profiles to process.")

        for profile_path in profile_files:
            print("#" * 80)
            print(f"Processing Customer Profile: {profile_path.name}")
            print("#" * 80)

            try:
                # Pass the specific profile path to the generation method
                recommendations, metrics = self.generate_recommendations(profile_path)
                
                # Create a subdirectory for this specific profile's results
                profile_output_dir = self.run_output_dir / profile_path.stem
                profile_output_dir.mkdir(exist_ok=True)
                
                if recommendations:
                    # Save run artifacts (prompts, data) for traceability
                    self.save_run_artifacts(profile_output_dir)

                    self.print_recommendations(recommendations)
                    self.print_performance_metrics(metrics)
                    
                    self.save_performance_metrics_to_json(metrics, profile_output_dir)
                    self.save_recommendations_to_json(recommendations, profile_output_dir)
                    self.save_conversations_to_json(metrics.agent_interactions, profile_output_dir)
                    # Pass the specific profile path to the summary function
                    self.save_run_summary_to_json(metrics, recommendations, profile_path.name, profile_output_dir)

                    print(f"\n📄 Results for {profile_path.name} saved to: {profile_output_dir}")
                    print(f"\n✅ Successfully processed {profile_path.name}!")
                    print(f"📊 Generated {len(recommendations)} recommendations in {metrics.total_processing_time:.2f}s")
                else:
                    print(f"No recommendations generated for {profile_path.name}.")

            except Exception as e:
                logger.error(f"Failed to process profile {profile_path.name}: {e}", exc_info=True)
                print(f"\n❌ Error processing profile {profile_path.name}: {e}")

    def save_run_artifacts(self, output_dir: Path):
        """Copies all essential run artifacts to the output directory for traceability."""
        try:
            # Copy source data csv
            source_csv_path = Path(self.data_manager.csv_path)
            shutil.copy(source_csv_path, output_dir / source_csv_path.name)

            # Copy agent profiles
            shutil.copy(self.customer_profiler_agent.agent_profile_path, output_dir / self.customer_profiler_agent.agent_profile_path.name)
            shutil.copy(self.listings_curator_agent.agent_profile_path, output_dir / self.listings_curator_agent.agent_profile_path.name)
            
            # Copy the specific customer profile for this run
            shutil.copy(self.current_customer_profile_path, output_dir / self.current_customer_profile_path.name)

            logger.info(f"Saved run artifacts (CSV, Agent Profiles) to {output_dir}")
        except Exception as e:
            logger.error(f"Could not save run artifacts: {e}")

    def print_agent_conversation(self, metrics: PerformanceMetrics):
        """Print the detailed agent conversation log."""
        print("\n" + "="*80)
        print("AGENT CONVERSATION LOG")
        print("="*80)
        
        for i, interaction in enumerate(metrics.agent_interactions, 1):
            print(f"\n🔄 Interaction {i}: {interaction.agent_name}")
            print(f"📝 Action: {interaction.action}")
            print(f"⏱️  Time: {interaction.processing_time:.2f}s")
            print(f"📊 Tokens: ~{interaction.token_count_estimate}")
            print(f"📤 PROMPT ({len(interaction.prompt)} chars):")
            print("-" * 40)
            # Show first 500 chars of prompt for readability
            prompt_preview = interaction.prompt[:500] + "..." if len(interaction.prompt) > 500 else interaction.prompt
            print(prompt_preview)
            print("-" * 40)
            print(f"📥 RESPONSE ({len(interaction.response)} chars):")
            print("-" * 40)
            # Show first 1000 chars of response for readability
            response_preview = interaction.response[:1000] + "..." if len(interaction.response) > 1000 else interaction.response
            print(response_preview)
            print("="*80)
    
    def print_performance_metrics(self, metrics: PerformanceMetrics):
        """Print detailed performance metrics."""
        print("\n" + "="*80)
        print("PERFORMANCE METRICS")
        print("="*80)
        
        print(f"⏱️  Total Processing Time: {metrics.total_processing_time:.2f} seconds")
        print(f"🏠 Properties Processed: {metrics.properties_processed}")
        print(f"💰 Properties After Budget Filter: {metrics.properties_filtered}")
        print(f"🎯 Properties Curated: {metrics.properties_curated}")
        print(f"📊 Properties Scored: {metrics.properties_scored}")
        print(f"📈 Average Appropriateness Score: {metrics.avg_appropriateness_score:.1f}/100")
        print(f"🏆 Best Score: {metrics.max_appropriateness_score}/100")
        print(f"📉 Lowest Score: {metrics.min_appropriateness_score}/100")
        print(f"✅ Success Rate (≥70 score): {metrics.success_rate:.1f}%")
        print(f"🤖 Agent Interactions: {len(metrics.agent_interactions)}")
        
        total_tokens = sum(i.token_count_estimate for i in metrics.agent_interactions)
        total_agent_time = sum(i.processing_time for i in metrics.agent_interactions)
        
        print(f"🔤 Estimated Total Tokens: ~{total_tokens:,}")
        print(f"⚡ Agent Processing Time: {total_agent_time:.2f}s")
        print(f"🔧 System Overhead: {metrics.total_processing_time - total_agent_time:.2f}s")
        
        # Agent breakdown
        customer_profiler_interactions = [i for i in metrics.agent_interactions if "Profiler" in i.agent_name]
        listings_curator_interactions = [i for i in metrics.agent_interactions if "Curator" in i.agent_name]
        
        print(f"\n👤 Customer Profiler Agent:")
        print(f"   Interactions: {len(customer_profiler_interactions)}")
        print(f"   Time: {sum(i.processing_time for i in customer_profiler_interactions):.2f}s")
        print(f"   Tokens: ~{sum(i.token_count_estimate for i in customer_profiler_interactions):,}")
        
        print(f"\n🏠 Listings Curator Agent:")
        print(f"   Interactions: {len(listings_curator_interactions)}")
        print(f"   Time: {sum(i.processing_time for i in listings_curator_interactions):.2f}s")
        print(f"   Tokens: ~{sum(i.token_count_estimate for i in listings_curator_interactions):,}")
        
        print("="*80)
    
    def save_performance_metrics_to_json(self, metrics: PerformanceMetrics, output_dir: Path):
        """Save detailed performance metrics to a JSON file."""
        filepath = output_dir / "performance_metrics.json"
        
        metrics_data = {
            "timestamp": time.time(),
            "metrics": metrics.to_dict(),
            "agent_interactions": [
                i.to_dict() for i in metrics.agent_interactions
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(metrics_data, f, indent=2)
    
    def save_recommendations_to_json(self, recommendations: List[PropertyRecommendation], output_dir: Path):
        """Saves the list of recommendations to a JSON file."""
        filepath = output_dir / "recommendations.json"
        recs_data = [rec.to_dict() for rec in recommendations]
        with open(filepath, 'w') as f:
            json.dump(recs_data, f, indent=2)

    def save_conversations_to_json(self, interactions: List[AgentInteraction], output_dir: Path):
        """Saves the agent conversation log to a JSON file."""
        filepath = output_dir / "conversations.json"
        interactions_data = [i.to_dict() for i in interactions]
        with open(filepath, 'w') as f:
            json.dump(interactions_data, f, indent=2)

    def save_run_summary_to_json(self, metrics: PerformanceMetrics, recommendations: List[PropertyRecommendation], profile_name: str, output_dir: Path):
        """Save a high-level summary of the run to JSON."""
        if not recommendations:
            top_recommendation_id = None
            avg_score = 0
            recommendations_list = []
        else:
            # Sort recommendations to find the best one
            recommendations.sort(key=lambda r: r.appropriateness_score, reverse=True)
            top_recommendation_id = recommendations[0].property_id
            avg_score = sum(r.appropriateness_score for r in recommendations) / len(recommendations)
            recommendations_list = [
                {"property_id": r.property_id, "title": r.title, "appropriateness_score": r.appropriateness_score}
                for r in recommendations
            ]

        # Get the filenames of the markdown files that will be saved as artifacts
        customer_profiler_agent_md = Path(self.customer_profiler_agent.agent_profile_path).name
        listings_curator_agent_md = Path(self.listings_curator_agent.agent_profile_path).name
        customer_profile_md = self.current_customer_profile_path.name
        source_csv_filename = Path(self.data_manager.csv_path).name

        output_files_dict = {
            "recommendations": "recommendations.json",
            "performance_metrics": "performance_metrics.json",
            "conversations": "conversations.json",
            "customer_profiler_agent": customer_profiler_agent_md,
            "listings_curator_agent": listings_curator_agent_md,
            "customer_profile": customer_profile_md,
            "source_data_csv": source_csv_filename,
        }

        summary = {
            "run_timestamp": datetime.now().isoformat(),
            "customer_profile": profile_name,
            "performance_overview": {
                "total_processing_time": f"{metrics.total_processing_time:.2f}s",
                "properties_processed": metrics.properties_processed,
                "properties_scored": metrics.properties_scored,
                "llm_interactions": len(metrics.agent_interactions),
            },
            "recommendation_overview": {
                "recommendations_generated": len(recommendations),
                "top_recommendation_id": top_recommendation_id,
                "average_appropriateness_score": f"{avg_score:.2f}",
                "recommendations": recommendations_list,
            },
            "output_files": output_files_dict
        }

        summary_path = output_dir / "run_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=4)
        logger.info(f"Saved run summary to {summary_path}")

    def print_recommendations(self, recommendations: List[PropertyRecommendation]):
        """Print formatted recommendations to console."""
        print("\n" + "="*80)
        print("PROPERTY RECOMMENDATIONS")
        print("="*80)
        
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec.title}")
            print(f"   Property ID: {rec.property_id}")
            print(f"   Price: £{rec.price:,.0f}")
            print(f"   Bedrooms: {rec.bedrooms} | Bathrooms: {rec.bathrooms}")
            print(f"   Type: {rec.property_type} | Location: {rec.location}")
            print(f"   Appropriateness Score: {rec.appropriateness_score}/100")
            print(f"   Key Features: {', '.join(rec.key_features)}")
            print(f"   Reasoning: {rec.reasoning}")
            print("-" * 80)


def main():
    """Main function to run the property recommendation application."""
    print("🏠 Property Recommendation System with Performance Analytics")
    print("=" * 60)
    
    # Configuration
    csv_path = "files/csv/listings_20250627_215417.csv"
    customer_profile_path = "src/agents_sdk_poc/customer_profiles"
    
    # Allow command line override of paths
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    if len(sys.argv) > 2:
        customer_profile_path = sys.argv[2]
    
    try:
        # Initialize application
        app = PropertyRecommendationApp(csv_path, customer_profile_path)
        app.run_for_all_profiles()
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 