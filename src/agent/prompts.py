# -*- coding: utf-8 -*-
SYSTEM_PROMPT = (
    "You are a Text-to-SQL agent that converts natural language questions into SQL queries.\n\n"
    "Important rules:\n"
    "1. Only use table and column names that exist in the schema. Do not hallucinate new ones.\n"
    "2. The generated SQL must be in a single-line format. Do not use newline characters.\n"
    "3. Prefer using the provided example values to construct WHERE conditions.\n"
    "4. Carefully check JOIN conditions and foreign key relationships.\n"
    "5. If an error occurs, precisely fix the SQL according to the error message.\n"
)

# Schema Linker prompt template
SCHEMA_LINKER_PROMPT_TEMPLATE = (
    "Given a natural language question and the full database schema, identify the tables that are relevant to the question.\n\n"
    "Question: {question}\n\n"
    "Full database schema:\n{db_schema}\n\n"
    "Carefully analyze the keywords in the question (such as table names, column names, and entity names) and identify the relevant tables.\n"
    "Return only the list of relevant table names in JSON array format, for example: [\"table1\", \"table2\"]\n"
    "Do not include any other explanation or text; return only the JSON array."
)

# Content Retriever prompt template
CONTENT_RETRIEVER_PROMPT_TEMPLATE = (
    "Given a natural language question and the relevant database schema, identify potential key values in the question (such as person names, locations, organizations, product names, specific times, numeric thresholds, etc.).\n\n"
    "Question: {question}\n\n"
    "Relevant schema:\n{relevant_schema}\n\n"
    "Extract the key values from the question (such as person names, locations, organizations, product names, specific times, numeric thresholds, etc.).\n"
    "Return only the list of key values in JSON array format, for example: [\"value1\", \"value2\"]\n"
    "If there are no explicit key values in the question, return an empty array: []\n"
    "Do not include any other explanation or text; return only the JSON array."
)

GENERATE_SQL_PROMPT = (
    "Generate an SQL query based on the following information:\n"
    "- Question: {question}\n"
    "- Relevant schema:\n{relevant_schema}\n"
    "- Example values: {retrieved_values}\n\n"
    "Produce an accurate SQL query in a single-line format (no newlines). Output only the SQL statement, with no additional explanation."
)

# ============================================================
# New: subproblem decomposition prompt
# ============================================================
SUBPROBLEM_PROMPT = (
    "You are an expert in decomposing questions into subproblems. Given a natural language question and the relevant database schema, "
    "break the question down into multiple SQL subproblems.\n\n"
    "Question: {question}\n\n"
    "Relevant schema:\n{relevant_schema}\n\n"
    "Analyze the question and identify which SQL clauses are needed (such as WHERE, GROUP BY, JOIN, ORDER BY, HAVING, LIMIT, etc.).\n"
    "Return a JSON object in the following format:\n"
    "{'subproblems': ["
    "{'clause': 'SELECT', 'expression': '...'}, "
    "{'clause': 'JOIN', 'expression': '...'}, ..."
    "]}\n\n"
    "Return only valid JSON. Do not include markdown markers or any extra explanation."
)

# ============================================================
# New: SQL plan prompt (COT + FINAL_PLAN)
# ============================================================
SQL_PLAN_PROMPT = (
    "You are an expert in designing SQL query plans. Using a Chain-of-Thought style, "
    "create a detailed SQL query plan for the given question.\n\n"
    "Question: {question}\n\n"
    "Relevant schema:\n{relevant_schema}\n\n"
    "Example values: {retrieved_values}\n\n"
    "Subproblem decomposition:\n{subproblems}\n\n"
    "Follow these steps:\n"
    "1. **Analyze the question**: Deeply understand the user intent and identify key information and constraints.\n"
    "2. **Map to the schema**: Determine which tables and columns are needed and how they should be joined.\n"
    "3. **Formulate the plan**: Create a step-by-step query plan, where each step corresponds to part of the SQL.\n\n"
    "Important notes:\n"
    "- The plan must be written in natural language.\n"
    "- Explicitly mention the table and column names used in each step.\n"
    "- Do NOT write the final SQL query.\n"
    "- All required tables must appear in the FROM and JOIN steps.\n"
    "- Clauses such as GROUP BY, HAVING, ORDER BY, and LIMIT must appear in the correct order.\n\n"
    "After your reasoning process, you must add a clear final section starting with 'FINAL_PLAN:' "
    "that summarizes your query plan in concise bullet points."
)

# ============================================================
# New: correction plan prompt (COT + CORRECTION_PLAN)
# ============================================================
CORRECTION_PLAN_PROMPT = (
    "You are a senior SQL debugging expert. Your task is to analyze a failed SQL query and, "
    "using Chain-of-Thought reasoning, create a clear correction plan. Do not write the corrected SQL directly.\n\n"
    "Original question: {question}\n\n"
    "Relevant schema:\n{relevant_schema}\n\n"
    "Failed SQL:\n{sql_draft}\n\n"
    "Execution error:\n{error}\n\n"
    "{semantic_issues}"
    "{correction_history}"
    "You are also an expert in error classification and understand the following error types:\n"
    "- schema.mismatch: Table or column names do not exist or are ambiguous.\n"
    "- join.logic_error: Incorrect JOIN conditions, wrong foreign keys, or unnecessary tables.\n"
    "- filter.condition_error: Errors in WHERE/HAVING clauses.\n"
    "- aggregation.grouping_error: Errors in aggregation functions or GROUP BY.\n"
    "- select.output_error: Errors in SELECT columns (extra, missing, or wrong order).\n"
    "- syntax.structural_error: Syntax errors or missing required clauses.\n"
    "- intent.semantic_error: Syntactically correct but does not match the user intent.\n\n"
    "Reasoning steps:\n"
    "1. **Locate the mismatch**: Compare the question, failed SQL, and schema to find the source of the error.\n"
    "2. **Identify the error type**: Decide the error type based on the above taxonomy.\n"
    "3. **Form a hypothesis**: Explain the root cause in one sentence (pay attention to subtle column name differences such as 'name' vs 'song_name').\n"
    "4. **Create a plan**: Write a clear, step-by-step correction plan.\n"
    "5. **Learn from history**: If there is correction history, avoid repeating previous mistakes.\n"
    "6. **Semantic issues**: If there are semantic validation issues, focus on whether the SQL intent matches the question.\n\n"
    "After your reasoning process, you must add a clear final section starting with 'CORRECTION_PLAN:' "
    "that summarizes your correction plan as concise steps."
)

# ============================================================
# New: generate corrected SQL based on the correction plan
# ============================================================
CORRECTION_SQL_PROMPT = (
    "You are a professional SQL correction expert. Based on the provided correction plan, generate a corrected SQL query.\n\n"
    "Original question: {question}\n\n"
    "Relevant schema:\n{relevant_schema}\n\n"
    "Incorrect SQL:\n{sql_draft}\n\n"
    "Correction plan:\n{correction_plan}\n\n"
    "Strictly follow the correction plan when modifying the SQL.\n"
    "Output only the final SQL query as a single line, without any explanations or extra characters."
)

# ============================================================
# New: SQL semantic validation prompt (SQL→Text back-translation + semantic consistency check)
# ============================================================
SEMANTIC_VALIDATE_PROMPT = (
    "You are an expert in SQL semantic validation. Your tasks are:\n"
    "1. Translate the given SQL query into a natural language explanation.\n"
    "2. Decide whether the SQL semantics are consistent with the original question.\n\n"
    "Original question: {question}\n\n"
    "Relevant schema:\n{relevant_schema}\n\n"
    "Generated SQL:\n{sql_draft}\n\n"
    "Please follow these steps:\n"
    "1. **SQL→Text translation**: Explain in natural language what this SQL query does, including:\n"
    "   - Which tables it queries.\n"
    "   - Which fields it selects.\n"
    "   - What filtering conditions it applies (WHERE).\n"
    "   - What aggregation or grouping it performs (GROUP BY, HAVING).\n"
    "   - What sorting or limits it applies (ORDER BY, LIMIT).\n\n"
    "2. **Semantic consistency check**: Compare the SQL semantics with the original question and identify issues such as:\n"
    "   - **field_error**: Whether the returned fields match the requirement of the question.\n"
    "   - **condition_error**: Whether the WHERE conditions are too strict or too loose.\n"
    "   - **join_error**: Whether table joins are correct, or if tables are missing or unnecessary.\n"
    "   - **aggregation_error**: Whether aggregation functions (COUNT/SUM/AVG, etc.) are correct.\n"
    "   - **sort_error**: Whether ORDER BY matches the question requirements.\n"
    "   - **limit_error**: Whether LIMIT is reasonable.\n\n"
    "Return the result as a JSON object with the following fields:\n"
    "- explanation: Natural language explanation of the SQL (string).\n"
    "- semantic_match: Whether the semantics match (true or false).\n"
    "- issues: A list of issues (array, each item has 'type' and 'description').\n\n"
    "Example format:\n"
    "{\"explanation\": \"This SQL queries the singer table and counts all singers.\", \"semantic_match\": true, \"issues\": []}\n\n"
    "Important: Return a pure JSON object only. Do NOT include any markdown markers (such as ```json or ```), or any extra explanation text."
)
