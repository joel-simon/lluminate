import os
import json
import uuid
import time
import logging
import numpy as np
from enum import Enum
import torch
from typing import List, Dict, Any, Optional, Union

# from evolution4 import generate_evolve_ideas
from shaderToImage import shader_to_image

# Global LLM client
from models import llm_client, text_embedder, image_embedder
from utils import extractCode

# defaultModel = "openai:3o-mini"
defaultModel = "openai:gpt-4o-mini"


class PhenotypeFormat(Enum):
    """Enum defining the format of an artifact's phenotype"""

    TEXT = "text"
    IMAGE = "image"


class Artifact:
    """Base class for creative artifacts with idea, genome, and phenome components"""

    def __init__(self, id: str = None):
        self.id = id or str(uuid.uuid4())
        self.idea = None  # String description of the idea
        self.genome = None  # Code or prompt
        self.phenome = None  # Path to the rendered phenotype
        self.prompt = None  # Original generation prompt
        self.embedding = None
        self.fitness = None
        self.creation_time = time.time()
        self.metadata = {}

    @property
    def phenotype_format(self) -> PhenotypeFormat:
        """Returns the format of this artifact's phenotype"""
        raise NotImplementedError("Subclasses must implement this")

    @classmethod
    def create_random(cls, prompt: str, output_dir: str, **kwargs):
        """Generate a random artifact directly (no explicit idea) and render it"""
        raise NotImplementedError("Subclasses must implement this")

    # @classmethod
    # def from_idea(cls, idea: str, output_dir: str, prompt: str = None, **kwargs):
    #     """Create an artifact by implementing the given idea and render it"""
    #     raise NotImplementedError("Subclasses must implement this")

    @classmethod
    def from_genome(cls, genome: str, output_dir: str, prompt: str = None, **kwargs):
        """Create an artifact from an existing genome and render it"""
        raise NotImplementedError("Subclasses must implement this")

    def render_phenotype(self, output_dir: str, **kwargs) -> Optional[str]:
        """Render the phenotype from the genome"""
        raise NotImplementedError("Subclasses must implement this")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization"""
        embedding = (
            self.embedding.cpu().numpy().tolist()
            if self.embedding is not None
            else None
        )
        return {
            "id": self.id,
            "idea": self.idea,
            "genome": self.genome,
            "phenome": self.phenome,
            "prompt": self.prompt,
            "embedding": embedding,
            "fitness": self.fitness,
            "creation_time": self.creation_time,
            "metadata": self.metadata,
            "type": self.__class__.__name__,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create from a dictionary"""
        raise NotImplementedError("Subclasses must implement this")

    def save(self, output_dir: str):
        """Save to disk"""
        os.makedirs(output_dir, exist_ok=True)
        artifact_path = os.path.join(output_dir, f"{self.id}.json")
        with open(artifact_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return artifact_path

    def crossover_with(
        self,
        other_artifacts: List["Artifact"],
        crossover_idea: str,
        output_dir: str,
        **kwargs,
    ):
        """Create a new artifact by crossing over this artifact with others"""
        raise NotImplementedError("Subclasses must implement this")


class ShaderArtifact(Artifact):
    systemPrompt = """You are an expert in creating WebGL 1.0 fragment shaders.
    Return valid webgl fragment shader.
    Provide the full fragment shader code without explanation.
    You can only use these uniforms:
	varying vec2 uv;
	uniform float time;
    """

    @property
    def phenotype_format(self) -> PhenotypeFormat:
        return PhenotypeFormat.IMAGE

    @classmethod
    def create_random(cls, prompt: str, output_dir: str, **kwargs):
        """Generate a random shader directly from a prompt and render it"""
        artifact = cls()
        artifact.prompt = prompt

        response = llm_client.chat.completions.create(
            model=defaultModel,
            messages=[
                {"role": "system", "content": ShaderArtifact.systemPrompt},
                {"role": "user", "content": f"User prompt: {prompt}"},
            ],
        )

        artifact.genome = extractCode(response.choices[0].message.content.strip())
        print(artifact.genome)
        artifact.render_phenotype(output_dir, **kwargs)
        return artifact

    # @classmethod
    # def from_idea(cls, idea: str, output_dir: str, prompt: str = None, **kwargs):
    #     """Create a shader by implementing the given idea and render it"""
    #     artifact = cls()
    #     artifact.idea = idea
    #     artifact.prompt = prompt

    #     # Generate shader code from idea
    #     implementation_prompt = f"""
    #     IDEA: {idea}

    #     PROMPT: {prompt or "Create an interesting shader"}

    #     Create a WebGL fragment shader based on this idea.
    #     Provide only the shader code without explanation.
    #     """

    #     response = llm_client.chat.completions.create(
    #         model="openai:gpt-4o-mini",
    #         messages=[{"role": "user", "content": implementation_prompt}],
    #     )

    #     # Set artifact properties
    #     artifact.genome = response.choices[0].message.content.strip()

    #     # Render phenotype immediately
    #     artifact.render_phenotype(output_dir, **kwargs)

    #     return artifact

    @classmethod
    def from_genome(cls, genome: str, output_dir: str, prompt: str = None, **kwargs):
        """Create a shader artifact from existing code and render it"""
        artifact = cls()
        artifact.genome = genome
        artifact.prompt = prompt

        # Add metadata if provided
        if "metadata" in kwargs:
            artifact.metadata = kwargs["metadata"]
        if "parent_id" in kwargs:
            artifact.metadata["parent_id"] = kwargs["parent_id"]

        # Render phenotype immediately
        artifact.render_phenotype(output_dir, **kwargs)

        return artifact

    def render_phenotype(self, output_dir: str, **kwargs) -> Optional[str]:
        """Render the shader to an image"""
        os.makedirs(output_dir, exist_ok=True)

        # In a real implementation, this would call a renderer with the shader code
        # For now, we'll just create a placeholder file
        output_path = os.path.join(output_dir, f"{self.id}.png")

        shader_to_image(self.genome, output_path, 768, 768, uniforms={"time": 0})

        self.phenome = output_path

        return self.phenome

    def crossover_with(
        self,
        other_artifacts: List[Artifact],
        crossover_idea: str,
        output_dir: str,
    ):
        """Create a new artifact by crossing over this artifact with others"""
        # Combine this artifact with others
        parents = [self] + other_artifacts

        # Format parent code snippets
        parent_codes = []
        for i, parent in enumerate(parents):
            code_snippet = parent.genome
            parent_codes.append(f"Parent {i+1}:\n```\n{code_snippet}\n```")

        # Create crossover prompt
        crossover_prompt = f"""
        EDIT IDEA: {crossover_idea}
        
        PARENT CODES:
        {"\n\n".join(parent_codes)}
        """

        response = llm_client.chat.completions.create(
            model=defaultModel,
            messages=[
                {"role": "system", "content": ShaderArtifact.systemPrompt},
                {"role": "user", "content": crossover_prompt},
            ],
        )

        # Create the crossover artifact
        crossover_code = extractCode(response.choices[0].message.content.strip())
        artifact = ShaderArtifact.from_genome(
            genome=crossover_code,
            output_dir=output_dir,
            prompt=self.prompt,
            metadata={
                "parent_ids": [p.id for p in parents],
                "crossover_idea": crossover_idea,
            },
        )

        return artifact

    # def mutate(self, mutation_idea: str, output_dir: str, **kwargs):
    #     """Create a mutated version of this artifact based on the mutation idea"""
    #     # Generate the mutated shader code
    #     mutation_prompt = f"""
    #     ORIGINAL PROMPT: {self.prompt}

    #     MUTATION IDEA: {mutation_idea}

    #     CURRENT CODE:
    #     ```
    #     {self.genome}
    #     ```

    #     Create a WebGL fragment shader based on this mutation idea.
    #     Provide only the shader code without explanation.
    #     """

    #     response = llm_client.chat.completions.create(
    #         model="openai:gpt-4o-mini",
    #         messages=[{"role": "user", "content": mutation_prompt}],
    #     )

    #     # Create a new artifact with the mutated genome
    #     mutated_code = response.choices[0].message.content.strip()
    #     mutated = ShaderArtifact.from_genome(
    #         genome=mutated_code,
    #         output_dir=output_dir,
    #         prompt=self.prompt,
    #         metadata={"parent_id": self.id, "mutation_idea": mutation_idea},
    #     )

    #     return mutated

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create from a dictionary"""
        artifact = cls(id=data["id"])
        artifact.idea = data.get("idea")
        artifact.genome = data.get("genome")
        artifact.phenome = data.get("phenome")
        artifact.prompt = data.get("prompt")
        artifact.fitness = data.get("fitness")
        artifact.creation_time = data.get("creation_time", time.time())
        artifact.metadata = data.get("metadata", {})

        if data.get("embedding") is not None:
            artifact.embedding = torch.tensor(data["embedding"])

        return artifact
