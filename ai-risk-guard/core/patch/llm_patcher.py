"""
LLM-based Patch Generation Engine.
Uses Gemini 1.5 Flash via the modern google-genai SDK.
"""

import os
from google import genai
from google.genai import types
from typing import List, Dict, Any, Optional
from utils.logger import logger

class LLMPatcher:
    """
    Service to generate multiple secure code patch candidates using LLMs.
    """

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found. LLM patching will be disabled.", "PATCH")
            self.enabled = False
            self.client = None
        else:
            try:
                # Stage 1: Attempt standard initialization
                self.client = genai.Client(api_key=api_key)
                
                # Stage 2: Verify model and API version
                # If this fails, we'll try to list models
                self.model_id = 'gemini-1.5-flash'
                try:
                    self.client.models.get(model=self.model_id)
                except Exception:
                    # Stage 3: Dynamic Discovery
                    logger.info("Standard model ID failed, discovering available models...", "PATCH")
                    for m in self.client.models.list():
                        if 'flash' in m.name.lower():
                            self.model_id = m.name
                            break

                logger.info(f"LLM Patcher active (Model: {self.model_id})", "PATCH")
                self.enabled = True
            except Exception as e:
                logger.error(f"LLM Patcher initialization failed: {e}", "PATCH")
                self.enabled = False

    def generate_candidates(self, code: str, vulnerabilities: List[Dict[str, Any]], n: int = 3) -> List[str]:
        """
        Generate N secure variants of the provided code.
        """
        if not self.enabled or not self.client:
            return [code] # Fallback to original code if disabled

        # Construct the context-aware prompt
        vuln_descriptions = "\n".join([
            f"- {v['type']} at line {v['line']}: {v['message']}" 
            for v in vulnerabilities
        ])

        prompt = f"""
You are an Expert Security Researcher and Senior Python Engineer.

### CONTEXT
The following Python code contains critical vulnerabilities. Your task is to provide {n} distinct, high-quality remediated versions of this code.

### DETECTED VULNERABILITIES
{vuln_descriptions}

### REMEDIATION REQUIREMENTS
1. FIX ALL: Every variant MUST address all listed vulnerabilities.
2. FUNCTIONAL PARITY: Maintain the original business logic. Do not remove features unless they are fundamentally insecure.
3. SECURITY FIRST:
   - Replace `os.system` with `subprocess.run(..., shell=False)`.
   - Replace `eval`/`exec` with `ast.literal_eval` or safe logical equivalents.
   - Replace `pickle`/`marshal` with `json` or `msgpack`.
   - Move secrets to `os.getenv` or `os.environ`.
4. CODE QUALITY: Use PEP 8 standards. Include robust error handling (try/except) for new security logic.
5. STRICT OUTPUT: Return ONLY the Python code. No preamble, no explanation text.

### FORMAT
Separate the {n} variants using this exact marker: ---VARIANT_BOUNDARY---

### CODE TO REMEDIATE
```python
{code}
```
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            content = response.text
            
            # Split variants based on the boundary
            candidates = content.split("---VARIANT_BOUNDARY---")
            
            # Clean up Markdown artifacts if LLM included them
            cleaned_candidates = []
            for c in candidates:
                cleaned = c.strip()
                if cleaned.startswith("```python"):
                    cleaned = cleaned[9:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned_candidates.append(cleaned.strip())
                
            logger.info(f"Generated {len(cleaned_candidates)} patch candidates via LLM", "PATCH")
            return cleaned_candidates

        except Exception as e:
            logger.error(f"LLM Patch generation failed: {e}", "PATCH")
            return [code]
