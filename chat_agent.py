#!/usr/bin/env python3
"""
Chat Agent Module
Handles AI chat functionality and employee queries
"""

import json
import time
import logging
import ast
import re
import pandas as pd
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from sqlalchemy import text

from config import (
    BEDROCK_MODEL_ID, BEDROCK_TEXT_MODEL_ID, AWS_REGION, 
    TEST_BEDROCK_ON_STARTUP, DB_ENGINE, BACKUP_CSV
)
from utils import extract_json_string, fallback_extract_field_name

class ChatAgent:
    """Agent 4: OpenRouter Chat Integration with Employee Lookup"""
    
    def __init__(self):
        # Use Nova Lite for text generation
        self.model_id = BEDROCK_MODEL_ID
        self.text_model_id = BEDROCK_TEXT_MODEL_ID
        self.fallback_models = [
            "amazon.nova-lite-v1:0",
            "anthropic.claude-3-sonnet-20240229-v1:0",
            "anthropic.claude-3-haiku-20240307-v1:0"
        ]
        logging.info(
            f"Initializing ChatAgent with Bedrock model: {self.text_model_id}"
        )
        self.bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=AWS_REGION
        )
        
        # Current user tracking
        self.current_user = None
        
        # Test Bedrock connectivity (optional)
        if TEST_BEDROCK_ON_STARTUP:
            self.test_bedrock_connection()
        
    def ask_bedrock(self, prompt):
        """Make API call to AWS Bedrock using robust dual-schema for Nova Lite.
        Tries messages-based chat schema first, then falls back to text schema automatically.
        """
        def parse_bedrock_response(body: dict) -> str:
            # Try multiple known response shapes across providers
            if not isinstance(body, dict):
                return ""
            # Nova text style
            if "outputText" in body and isinstance(body["outputText"], str):
                return body["outputText"]
            # Claude/content style
            if "content" in body and isinstance(body["content"], list) and body["content"]:
                first = body["content"][0]
                if isinstance(first, dict):
                    if "text" in first and isinstance(first["text"], str):
                        return first["text"]
                    if "type" in first and first.get("type") == "text" and isinstance(first.get("text"), str):
                        return first.get("text", "")
            # Nova chat style: output.message.content[0].text
            if "output" in body and isinstance(body["output"], dict):
                msg = body["output"].get("message")
                if isinstance(msg, dict):
                    content = msg.get("content")
                    if isinstance(content, list) and content:
                        c0 = content[0]
                        if isinstance(c0, dict) and isinstance(c0.get("text"), str):
                            return c0.get("text", "")
            # Generic fallbacks
            for key in ("generation", "completion", "text"):
                if key in body and isinstance(body[key], str):
                    return body[key]
            return ""

        try:
            logging.info(
                f"Bedrock request -> model={self.text_model_id}, prompt_len={len(prompt)}"
            )

            # Primary: messages-based chat schema (works with Nova chat interface)
            chat_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": prompt}
                        ],
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 120,
                    "temperature": 0.6,
                    "topP": 0.9,
                },
            }

            start_time = time.time()
            try:
                response = self.bedrock_client.invoke_model(
                    modelId=self.text_model_id,
                    body=json.dumps(chat_body),
                    contentType="application/json",
                    accept="application/json",
                )
                response_body = json.loads(response["body"].read())
                latency_ms = int((time.time() - start_time) * 1000)
                logging.info(
                    f"Bedrock response <- model={self.text_model_id} (messages), latency_ms={latency_ms}"
                )
                reply = parse_bedrock_response(response_body)
                if reply:
                    return reply
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                msg = e.response.get("Error", {}).get("Message")
                # Do not spam errors; treat as schema mismatch and try text schema silently
                if code != "ValidationException":
                    logging.warning(f"Bedrock messages-schema call failed: {code}: {msg}")
                else:
                    logging.info(f"Validation indicates alternate schema is required: {msg}")

            # Secondary: text-generation schema (legacy Nova Lite)
            text_body = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 120,
                    "temperature": 0.6,
                    "topP": 0.9,
                },
            }
            start_time = time.time()
            response = self.bedrock_client.invoke_model(
                modelId=self.text_model_id,
                body=json.dumps(text_body),
                contentType="application/json",
                accept="application/json",
            )
            response_body = json.loads(response["body"].read())
            latency_ms = int((time.time() - start_time) * 1000)
            logging.info(
                f"Bedrock response <- model={self.text_model_id} (text), latency_ms={latency_ms}"
            )
            reply = parse_bedrock_response(response_body)
            if reply:
                return reply
            
            # If still nothing parsed, try fallbacks
            logging.info("Primary model returned empty content; trying fallback models")
            return self.try_fallback_models(prompt)

        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            msg = e.response.get("Error", {}).get("Message")
            # Prefer graceful fallback instead of raising noisy errors
            logging.warning(f"Bedrock client error on primary model: {code}: {msg}")
            return self.try_fallback_models(prompt)
        except Exception as e:
            logging.error(f"Chat API error: {e}")
            return "I'm sorry, I'm having trouble connecting to my brain right now."
    
    def try_fallback_models(self, prompt):
        """Try alternative Bedrock models if the primary one fails.
        Uses messages schema for Nova first, with automatic fallback to text schema.
        """
        for model_id in self.fallback_models:
            if model_id == self.text_model_id:
                continue  # Skip the current model

            try:
                logging.info(f"Trying fallback model: {model_id}")

                if "claude" in model_id.lower():
                    request_body = {
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt,
                            }
                        ],
                        "max_tokens": 1000,
                        "temperature": 0.65,
                        "top_p": 0.9,
                        "anthropic_version": "bedrock-2023-05-31",
                    }
                    response = self.bedrock_client.invoke_model(
                        modelId=model_id,
                        body=json.dumps(request_body),
                        contentType="application/json",
                        accept="application/json",
                    )
                    body = json.loads(response["body"].read())
                    if "content" in body and isinstance(body["content"], list) and body["content"]:
                        logging.info(f"✅ Fallback model {model_id} succeeded")
                        return body["content"][0].get("text", "")
                    continue

                if "nova" in model_id.lower():
                    # Try messages schema first
                    chat_body = {
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"text": prompt}
                                ],
                            }
                        ],
                        "inferenceConfig": {
                            "maxTokens": 1000,
                            "temperature": 0.65,
                            "topP": 0.9,
                        },
                    }
                    try:
                        response = self.bedrock_client.invoke_model(
                            modelId=model_id,
                            body=json.dumps(chat_body),
                            contentType="application/json",
                            accept="application/json",
                        )
                        body = json.loads(response["body"].read())
                        text = (
                            body.get("output", {})
                                .get("message", {})
                                .get("content", [{}])[0]
                                .get("text", "")
                        )
                        if text:
                            logging.info(f"✅ Fallback model {model_id} succeeded (messages)")
                            return text
                    except ClientError as e:
                        # Fall through to text schema on validation issues
                        pass

                    # Fallback: text-generation schema
                    text_body = {
                        "inputText": prompt,
                        "textGenerationConfig": {
                            "maxTokenCount": 1000,
                            "temperature": 0.65,
                            "topP": 0.9,
                        },
                    }
                    response = self.bedrock_client.invoke_model(
                        modelId=model_id,
                        body=json.dumps(text_body),
                        contentType="application/json",
                        accept="application/json",
                    )
                    body = json.loads(response["body"].read())
                    if "outputText" in body and isinstance(body["outputText"], str):
                        logging.info(f"✅ Fallback model {model_id} succeeded (text)")
                        return body["outputText"]

            except Exception as e:
                logging.warning(f"Fallback model {model_id} failed: {e}")
                continue

        # If all models fail, return a helpful message
        logging.error("All Bedrock models failed")
        return (
            "I'm sorry, I'm experiencing technical difficulties with all my AI models. "
            "Please try again later."
        )
    
    def test_bedrock_connection(self):
        """Test Bedrock connectivity and model availability"""
        try:
            logging.info("Testing Bedrock connectivity...")
            
            # Test with a simple prompt
            test_prompt = "Hello, this is a test."
            test_response = self.ask_bedrock(test_prompt)
            
            if test_response and len(test_response) > 0:
                logging.info("✅ Bedrock connection test successful")
            else:
                logging.warning("⚠️ Bedrock connection test completed with unexpected response")
                
        except Exception as e:
            logging.error(f"❌ Bedrock connection test failed: {e}")
            logging.warning("The bot may experience issues with AI responses")
            
        # Check available models
        self.check_available_models()
    
    def check_available_models(self):
        """Check which Bedrock models are available in the account"""
        try:
            bedrock_client = boto3.client("bedrock", region_name=AWS_REGION)
            response = bedrock_client.list_foundation_models()
            
            available_models = []
            for model in response.get("modelSummaries", []):
                if model.get("modelId") in self.fallback_models:
                    available_models.append(model["modelId"])
            
            if available_models:
                logging.info(f"✅ Available Bedrock models: {', '.join(available_models)}")
            else:
                logging.warning("⚠️ No preferred Bedrock models found in account")
                
        except Exception as e:
            logging.warning(f"Could not check available models: {e}")
    
    def extract_json_string(self, content):
        """Extract JSON string from content"""
        # Strip code fences if present
        if content:
            content = content.strip()
            if content.startswith("```"):
                content = content.strip('`')
                # remove optional json/lang tag
                content = re.sub(r'^(json|\w+)\n', '', content)
        patterns = [
            r'\{[^{}]*"field"[^{}]*"name"[^{}]*\}',  # JSON with field and name
            r'\{[^{}]+\}',  # Any JSON object
            r'field["\s]*:["\s]*["\']([^"\']+)["\'][^}]*name["\s]*:["\s]*["\']([^"\']+)["\']',  # Extract field and name directly
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                if pattern == patterns[2]:  # Direct field/name extraction
                    field = match.group(1)
                    name = match.group(2)
                    return json.dumps({"field": field, "name": name})
                else:
                    return match.group(0).strip()
        
        return None

    def fallback_extract_field_name(self, user_input: str):
        """Fallback extractor for field and name when model JSON is unavailable."""
        text_norm = user_input.strip()
        text_l = text_norm.lower()
        
        # Map synonyms to canonical fields (only allowed fields per new rules)
        field = None
        if any(k in text_l for k in ["email", "mail", "gmail", "e-mail"]):
            field = "email"
        elif any(k in text_l for k in ["department", "dept"]):
            field = "department"
        elif any(k in text_l for k in ["phone", "mobile", "number", "contact"]):
            field = "phone"
        elif any(k in text_l for k in ["salary", "pay", "ctc", "earn", "income", "compensation"]):
            field = "salary"  # Will be blocked in main function
        else:
            field = "name"  # Default to general information

        # Try regex patterns for names
        name = None
        patterns = [
            r"(?:email|department|phone|salary|mobile|number) of ([A-Z][a-z]+(?: [A-Z][a-z]+)*)",
            r"([A-Z][a-z]+(?: [A-Z][a-z]+)*)'s (?:email|department|phone|salary|mobile|number)",
            r"what is (?:the )?(?:email|department|phone|salary|mobile|number) of ([A-Z][a-z]+(?: [A-Z][a-z]+)*)",
            r"tell me (?:about|the) ([A-Z][a-z]+(?: [A-Z][a-z]+)*)",
            r"([A-Z][a-z]+(?: [A-Z][a-z]+)*) (?:works|employee|staff)",
        ]
        
        for pat in patterns:
            m = re.search(pat, user_input, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                break
                
        # If still not found, collect capitalized tokens as a guess
        if not name:
            tokens = [t for t in re.findall(r"[A-Za-z']+", user_input) if t.istitle()]
            if len(tokens) >= 1:
                # Use up to first two title-cased tokens as a name guess
                name = " ".join(tokens[:2])

        if name:  # Return even if field is empty (for unknown field requests)
            return {"field": field or "name", "name": name}
        return None
    
    def process_employee_query(self, user_input):
        """Process employee information queries with strict JSON output rules"""
        try:
            # Rule 1: Only answer if the user is a recognized employee
            if not self.current_user or self.current_user == "Visitor":
                return json.dumps({"error": "Access denied. Only recognized employees can query employee information."})
            
            # Clean user input
            user_input = user_input.replace("'s", "").replace("'s", "")
            user_input = user_input.replace("gmail", "email").replace("Gmail", "email").replace("mail", "email").strip()

            # Extract the requested employee name and field
            prompt = (
                "You are a JSON extraction API for employee information. Your ONLY job is to extract employee information and return a valid JSON object.\n\n"
                "CRITICAL RULES:\n"
                "1. Return ONLY the JSON object, no other text, no explanations\n"
                "2. Use double quotes for JSON keys and string values\n"
                "3. The JSON must have exactly two keys: \"field\" and \"name\"\n"
                "4. If the person is not found or unclear, return: {\"field\": \"\", \"name\": \"\"}\n\n"
                "ALLOWED FIELDS:\n"
                "- \"email\" (for email, mail, gmail, e-mail)\n"
                "- \"department\" (for department, dept)\n"
                "- \"phone\" (for phone, mobile, number, contact)\n"
                "- \"name\" (for general information)\n\n"
                "EXAMPLES:\n"
                "Input: \"What is the email of Alice Smith\"\n"
                "Output: {\"field\": \"email\", \"name\": \"Alice Smith\"}\n\n"
                "Input: \"What is the phone number of John Doe\"\n"
                "Output: {\"field\": \"phone\", \"name\": \"John Doe\"}\n\n"
                "Input: \"Tell me about Shakti\"\n"
                "Output: {\"field\": \"name\", \"name\": \"Shakti\"}\n\n"
                "Input: \"What is the department of Mary Johnson\"\n"
                "Output: {\"field\": \"department\", \"name\": \"Mary Johnson\"}\n\n"
                f"Now extract from this input: '{user_input}'"
            )

            raw_content = self.ask_bedrock(prompt)
            logging.info(f"Raw AI response: {raw_content}")
            extracted = self.extract_json_string(raw_content)
            logging.info(f"Extracted content: {extracted}")

            if not extracted:
                logging.warning("Model did not return JSON; using fallback extractor")
                fb = self.fallback_extract_field_name(user_input)
                if not fb:
                    return json.dumps({"error": "Could not extract structured data from input."})
                field = fb["field"]; name = fb["name"]
            else:
                try:
                    data = json.loads(extracted)
                    field = data.get("field", "").strip()
                    name = data.get("name", "").strip()
                except json.JSONDecodeError:
                    # Try parsing with ast for non-strict JSON (single quotes, etc.)
                    try:
                        data = ast.literal_eval(extracted)
                        if isinstance(data, dict):
                            field = str(data.get("field", "")).strip()
                            name = str(data.get("name", "")).strip()
                        else:
                            logging.error("Parsed non-dict structure from model output")
                            return json.dumps({"error": "Error processing the model's response."})
                    except Exception as e2:
                        logging.error(f"JSON decode error: {e2}")
                        return json.dumps({"error": "Error processing the model's response."})

            if not name:
                logging.warning("Model did not return valid name.")
                return json.dumps({"error": "Employee name not specified."})

            # Rule 3: Never share salary information
            if field.lower() in ["salary", "pay", "ctc", "compensation"] or any(word in user_input.lower() for word in ["salary", "pay", "ctc", "compensation", "earn", "income"]):
                return json.dumps({"error": "Salary information cannot be shared."})

            # Search for employee in database first, then CSV fallback
            employee_data = None
            
            # Database Lookup
            try:
                with DB_ENGINE.connect() as conn:
                    logging.info(f"Querying database for {name}")
                    result = conn.execute(
                        text("SELECT name, department, phone_number, email FROM employees WHERE LOWER(name) = LOWER(:name)"),
                        {"name": name}
                    ).fetchone()
                    
                    if result:
                        employee_data = {
                            "name": result[0],
                            "department": result[1] if result[1] else "",
                            "phone": result[2] if result[2] else "",
                            "email": result[3] if result[3] else ""
                        }
            except Exception as e:
                logging.warning(f"Database lookup failed: {e}")

            # CSV Fallback if not found in database
            if not employee_data:
                try:
                    logging.info(f"Checking CSV backup for {name}")
                    df = pd.read_csv(BACKUP_CSV)
                    row = df[df["name"].str.lower() == name.lower()]
                    
                    if not row.empty:
                        employee_data = {
                            "name": row.iloc[0]["name"],
                            "department": row.iloc[0].get("department", ""),
                            "phone": row.iloc[0].get("phone_number", ""),
                            "email": row.iloc[0].get("email", "")
                        }
                except Exception as e:
                    logging.warning(f"CSV lookup failed: {e}")

            # Rule 5: If employee not found, return error
            if not employee_data:
                return json.dumps({"error": "Employee not found"})

            # Rule 2: Provide only requested field when a specific field is asked
            # Otherwise, provide the standard set (name, department, phone, email)
            field_l = (field or "").lower()
            if field_l in ("email", "phone", "department"):
                # Return only the specifically requested field
                return json.dumps({field_l: employee_data.get(field_l, "")})

            # Fallback/default: return the standard set
            response = {
                "name": employee_data["name"],
                "department": employee_data["department"],
                "phone": employee_data["phone"],
                "email": employee_data["email"]
            }
            return json.dumps(response)

        except Exception as e:
            logging.exception(f"Exception in process_employee_query: {e}")
            return json.dumps({"error": f"System error: {str(e)}"})
            
    def process_greeting(self, user_input):
        """Generate a natural greeting response like a human receptionist"""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            time_greeting = "Good Morning"
        elif 12 <= hour < 17:
            time_greeting = "Good Afternoon"
        else:
            time_greeting = "Good Evening"
            
        if "how are you" in user_input.lower():
            greeting = f"{time_greeting}! I'm doing well, thank you for asking. How can I help you today?"
        elif any(greeting in user_input.lower() for greeting in ["good morning", "good afternoon", "good evening"]):
            greeting = f"{time_greeting}! How can I assist you today?"
        else:
            greeting = f"Hi there! How can I assist you today?"
        return greeting
            
    def is_department_query(self, user_input):
        """Check if the user is asking about a department location"""
        department_keywords = [
            "where is", "location of", "find", "directions to", "how to get to",
            "where can i find", "where do i go for", "where's the", "where is the",
            "can you tell me where", "i need to find", "i'm looking for"
        ]
        department_names = [
            "hr", "human resources", "it", "information technology", "engineering",
            "finance", "marketing", "sales", "operations", "support", "department"
        ]
        
        user_lower = user_input.lower()
        
        # Check if it contains department location keywords
        has_location_keyword = any(keyword in user_lower for keyword in department_keywords)
        
        # Check if it mentions a department
        has_department = any(dept in user_lower for dept in department_names)
        
        # Additional check: if it contains "department" and location keywords, it's likely a department query
        if "department" in user_lower and has_location_keyword:
            return True
            
        # Check for specific patterns like "where is HR" or "HR department location"
        if has_location_keyword and has_department:
            return True
            
        return False

    def get_department_representative(self, department):
        """Get the primary representative for a department - Always Alex (office boy)"""
        # Alex handles all department queries as the office boy
        return "Alex"

    def process_department_query(self, user_input):
        """Handle department location queries by notifying the department representative"""
        # Extract department from query
        user_lower = user_input.lower()
        department = None
        
        if "hr" in user_lower or "human resources" in user_lower:
            department = "HR"
        elif "it" in user_lower or "information technology" in user_lower:
            department = "IT"
        elif "engineering" in user_lower:
            department = "Engineering"
        elif "finance" in user_lower:
            department = "Finance"
        elif "marketing" in user_lower:
            department = "Marketing"
        elif "sales" in user_lower:
            department = "Sales"
        elif "operations" in user_lower:
            department = "Operations"
        elif "support" in user_lower:
            department = "Support"
        else:
            department = "HR"  # Default to HR
        
        # Get the representative for this department
        representative = self.get_department_representative(department)
        
        # Return response and representative info for SMS notification
        response = f"Please wait here, Alex will come and assist you. I have notified him."
        
        return {
            "response": response,
            "representative": representative,
            "department": department
        }

    def process_general_query(self, user_input):
        """Process general conversation queries with natural responses"""
        prompt = f"""
        You are a professional human receptionist at a company. Respond naturally and professionally.
        Keep replies short and crisp: 1–2 sentences max, unless the user explicitly asks for details.
        Never mention that you are an AI; act like a real receptionist.
        
        User query: {user_input}
        """
        
        return self.ask_bedrock(prompt)
