                                                            

                       

query_generation_prompt = '''
You are given a coarse household task identifier and a set of success-critical end states for that task. Generate one natural user query that clearly expresses the required final results in human language.
Task identifier: {task_id}
Required end states: {goal_state}
Requirements:
(1) Preserve the core task goal, the main object(s), and every required end result in the input. Do NOT broaden the task into a more general activity, and do not omit any success-critical outcome.
(2) Preserve quantities, grouping relations, and end-state semantics exactly when they are present in the input (for example: both, all three, exactly two, in the same container, closed at the end, still on their plates, not broken).
(3) Do NOT add tools, materials, action order, user preferences, safety concerns, or background context that are not supported by the input. 
(4) Keep the question high-level and method-agnostic. Do NOT bake in a specific tool or solution path.
(5) Prefer a short user-facing question that naturally starts with "How do I" or "How can I" when possible.
(6) Output exactly one short question and nothing else. If the input is still too vague to form a clear household query, output only **REJECT**.
Your answer:'''

                    

filter_prompt = '''I only want questions about concrete household tasks, where a user wants to accomplish a practical task at home but does not know the steps and asks an agent to help plan or figure it out (for example: defrosting meat, installing a ceiling light, fixing a faucet, cleaning a washing machine).

- Do NOT include aesthetic or decoration-related questions (for example: how to decorate a room, how to match furniture, color choices, or other style-related topics).
- Do NOT include questions about reasons to do something (for example: why is my faucet leaking, why is my washing machine making noise).
- Do NOT include questions about what is something or how something works (for example: what is a ceiling light, how does a washing machine work).
- Do NOT include questions asking for plausibility or safety of an action (for example: is it safe to use bleach in a washing machine, can I put a metal pan in the microwave).
- Do NOT include tasks with a vague or underspecified goal (e.g., "fix a broken table" without specifying what is broken).
- Only include questions about realistic, everyday situations that could plausibly occur indoors in a home, even if they might also occur elsewhere.
- DO NOT include questions that require the agent to seek external assistance, such as purchasing items from outside the home, calling someone, or making appointments for in-home services.
- DO NOT include questions that explicitly require the agent to complete a task using a specific method or tool (e.g., “use a screwdriver to fix it”).

Next, I will give you a question. Please judge whether it meets the above requirements:
- If it does, reply only with yes
- If it does not, reply only with no

Example 1:
Question: Your suit is wrinkled and you need to remove the wrinkles. How do you remove the wrinkles from your suit?
Answer: yes
Example 2: You are at home and you accidentally dropped your key card down a narrow, deep vent. How do you retrieve your key card without seeking external help?
Answer: yes
Example 3: You are at home and your hose has sprung a leak. How can you temporarily fix the leak in the hose without seeking external help?
Answer: yes

Question: {Question}
You must answer only yes or no, and nothing else. Your answer is: '''

filter_task_id_prompt = '''I will give you a task identifier or a high-level task label, not necessarily a full question (for example, "adding_chemicals_to_hot_tub" or "Wash clothes"). Judge whether it can naturally correspond to a user asking an agent for help with a concrete household task at home.

- Do NOT include tasks that primarily require going outside the present environment, shopping, mailing, booking services, or interacting with external institutions.
- Do NOT include tasks involving overly specific entities (e.g., particular brands, proprietary products, or tasks requiring specialized technical knowledge). All tasks should be solvable using general common sense.
- Do NOT include tasks that already hard-code a specific method or tool (for example, "Wash dishes with dishwasher" or "Wash dishes by hand").

- Prefer higher-level household tasks that could plausibly admit multiple solution paths.
- You should adopt a tight and strict standard when applying the above criteria. If a task identifier or label does not clearly denote such a task, it should be rejected.

Next, I will give you a task identifier or task label. It may be an underscore-separated identifier or a short title-like phrase. Interpret it as a candidate household task, not as a complete user question:
- If it qualifies, reply only with yes
- If it does not, reply only with no

Task identifier / label: {task_phrase}
You must answer only yes or no, and nothing else. Your answer is: '''

shorten_prompt = '''Rewrite the following question into the simplest and most direct form. Remove all background information, explanations, and extra details. Keep only the core question.

Example:
Original question:
How can I add an outlet to a box where two cables join?
I have this space under my sink where there is this electrical box. If I had to guess, these pigtails are just connecting the 2 cables together, and the original owner had put it in a box in case of wanting to add an outlet here down the road. I have a multimeter. How can I test to verify my theory and what would the proper way to wire in an outlet in be?

Simplified question:
How can I add an outlet to a box where two cables join?

Now simplify this question:
Question: {Filtered_question}

Output only the simplified question. Do not include any other text.'''

                                                                
rewrite_prompt = '''Rewrite the following query into one short natural user question asking for help with the task. The output should sound like something a person would realistically ask, while staying faithful to the original task. 

## Requirements that you MUST FOLLOW:
(1) Preserve the core task goal and the main object(s) in the input. Do NOT broaden the task into a more general activity.
(2) Do NOT additionally add tools, materials, constraints, user preferences, safety concerns, or background context that are not present in the input.
(3) The rewritten question should be high-level and method-agnostic. Do NOT bake in a specific tool or solution path.
(4) The rewritten question should sound like a realistic household help request from a normal user.
(5) If the task takes place in an indoor setting similar to a household environment (e.g., a dorm or hotel), transfer the setting to a household environment without changing any other aspects of the task. If the original query does not take place in an indoor setting, output REJECT. 
(6) Output exactly one short question or REJECT, nothing else.

## Example
Example 1:
Raw question: You spilled red wine on the hotel carpet and want to clean it up before the housekeeping staff reports this. Tools available: a bottle opener, a plastic cup, a toothbrush, a bottle of mineral water that is sealed shut, a pack of sugar, a white bath towel, a bar of soap, a hair dryer. How do you clean up the wine stain using only these items?
Rewritten question: You are at home and you spilled red wine on the carpet and want to clean it up. How do you clean up the wine stain?
Example 2:
Raw question: The hotel bathroom door handle is broken and you can't exit. Tools available: a smartphone with low battery, a hair comb, a teaspoon, a toothbrush, a wire hanger, a hotel shoe horn, a bottle of lotion. The door handle doesn't have any openings. How do you get out using only these tools?
Rewritten question: Your are at the bathroom in your home, but the bathroom door handle is broken. How do you get out?
Example 3:
Raw question: The hotel's WiFi signal is weak and you have an important video call. Tools available: a luggage rack, a pierced tin can, a clothes hanger, a bedside lamp, chewing gum, a water bottle, aluminum foil. How do you boost the WiFi signal using only these items?
Rewritten question: You are at home and the WiFi signal is weak. How do you boost the WiFi signal without seeking external help?
Example 4:
Raw question: Your garden hose has sprung a leak, and you don't have a hose repair kit. Items available include an old tire tube, a plastic bag, a rubber band, duct tape, an inflatable pool ring, a beach ball, a pair of scissors and a spoon. The constraint here is that the hole in the hose is too large to be covered by just a rubber band and plastic bag. How can you temporarily fix the leak in the garden hose with these items?
Rewritten question: You are at home and your hose has sprung a leak. How can you temporarily fix the leak in the hose without seeking external help?

## Task identifier / label: {task_phrase}
Your answer: '''

                           
rewrite_macgyver_prompt = """
You are a careful query rewriter.

## Task
Rewrite the given question by removing all constraints and resource limitations,
while preserving the original scenario and the core task goal.

## Rules
(1) Preserve the core task goal and the main object(s) in the input. Do NOT broaden the task into a more general activity.
(2) Do NOT additionally add tools, materials, constraints, user preferences, safety concerns, or background context that are not present in the input.
(3) The rewritten question should be high-level and method-agnostic. Do NOT bake in a specific tool or solution path.
(4) The rewritten question should sound like a realistic household help request from a normal user.
(5) If the task takes place in an indoor setting similar to a household environment (e.g., a dorm or hotel), transfer the setting to a household environment without changing any other aspects of the task. If the original query does not take place in an indoor setting, output REJECT. 
(6) Highlight that 'You' are at home.
(7) Output exactly one short question or REJECT, nothing else.

## Example
Example 1:
Raw question: You spilled red wine on the hotel carpet and want to clean it up before the housekeeping staff reports this. Tools available: a bottle opener, a plastic cup, a toothbrush, a bottle of mineral water that is sealed shut, a pack of sugar, a white bath towel, a bar of soap, a hair dryer. How do you clean up the wine stain using only these items?
Rewritten question: You are at home and you spilled red wine on the carpet and want to clean it up. How do you clean up the wine stain?
Example 2:
Raw question: The hotel bathroom door handle is broken and you can't exit. Tools available: a smartphone with low battery, a hair comb, a teaspoon, a toothbrush, a wire hanger, a hotel shoe horn, a bottle of lotion. The door handle doesn't have any openings. How do you get out using only these tools?
Rewritten question: Your are at the bathroom in your home, but the bathroom door handle is broken. How do you get out?
Example 3:
Raw question: The hotel's WiFi signal is weak and you have an important video call. Tools available: a luggage rack, a pierced tin can, a clothes hanger, a bedside lamp, chewing gum, a water bottle, aluminum foil. How do you boost the WiFi signal using only these items?
Rewritten question: You are at home and the WiFi signal is weak. How do you boost the WiFi signal without seeking external help?
Example 4:
Raw question: You accidentally dropped your hotel key card down a narrow, deep vent and can't reach it by hand. Tools available: a hanger, a piece of thread, a too short selfie stick, a fork, a roll of duct tape, a rubber band, a straw. How do you retrieve your key card using only these items?
Rewritten question: You are at home and you accidentally dropped your key card down a narrow, deep vent. How do you retrieve your key card without seeking external help?


Raw question: {raw_question}
## Rewritten question:"""

                              
answer_candidate_sampling_prompt_one = '''
You are now in a housing environment. Given the question: {Question}, generate a step-by-step plans to accomplish the task.

Requirements:
1. For each step, clearly state which tools or entities are used, how they are used, and the correct order of operations.
2. All tool / entity names must be wrapped in ** **.
3. For every tool incorporated in the plan, you must clearly and concretely state what the tool is. Vague descriptions such as "something hard" or "existing heavy object" are not allowed.
4. You MUST NOT seek any external help. This includes, but is not limited to, calling someone, messaging someone, or searching for information online.
5. The plan must be fully deterministic. You MUST NOT include conditional logic such as “check X, and if Y happens, then do Z.” All steps must proceed directly without branching.
6. You may directly propose a concrete and complete plan without considering whether the required tools or objects are currently available in the environment (but don't use expressions like "existing xxx", simply use the object directly). If any required items are unavailable, the user will clarify in subsequent turns.
7. Definitions of tools/entities that you should list out:
    (1) **Exclude Body Parts**: Do NOT list human body parts (e.g., hands, feet, eyes) as tools or entities.
    (2) **Only Tangible Household Objects**: List only concrete household objects. Do NOT include natural elements or abstract conditions (e.g., sunlight, air, temperature, time, water).
    (3) **Structural Elements Are Implicit**: Floors, walls, ceilings, doors, and other permanent structural parts of the house are always present. Do NOT list them as tools or entities (e.g., Do NOT list "existing walls" as a tool / entity), though you may reference and use them in your plan.
    (4) **Single-Object Constraint**: Every tool or entity must be a single, specific object. You must NOT list multiple alternatives. Do NOT use words such as "or", "and/or", "optional", "etc.", or similar expressions that indicate alternatives or optional items. Each listed tool/entity must be exactly one concrete object.{resample_rule}


Output format for your plan:
<answer_start>
[Used Tools / Entities]: Write a comma-separated list of all tools or entities used in this plan. (**<Tool_1>**, **<Tool_2>**, ...)
[Step description]: Provide numbered steps. Each step must explain what to do, how to use the tools/entities, and in what order.

You may reason before <answer_start>, but once <answer_start> appears, do not output any additional reasoning, commentary, or analysis; output only the final answer. Now generate your plans for:
Question: {Question}
'''

resample_tools_rule = '''
\n\t(Important) **Basic rules**: You must not use any of the following tools / objects in your plan:
{gt_banned_tools}
'''

resample_prefs_rule = '''
\n\t(Important) **Basic rules**: Your generated plan must NOT reflect any of the following user preferences (that is, your plan may violate these user preferences or be completely unrelated to them, but it must not explicitly incorporate or demonstrate them):
{gt_banned_prefs}
'''

answer_candidate_sampling_prompt = '''
Given the question: {Question}, generate {verbal_sample_num} different step-by-step plans to accomplish the task.

Requirements:
1. Each plan must use a fundamentally different method or strategy, not just swapping tools or objects.
2. The generated plans must be fundamentally different from the original plan instead of just swapping tools or objects.
3. For each step, clearly state which tools or entities are used, how they are used, and the correct order of operations.
4. All tool / entity names must be wrapped in ** **.
5. For every tool incorporated in the plan, you must clearly and concretely state what the tool is. Vague descriptions such as "something hard" or "existing heavy object" are not allowed.
6. You MUST NOT seek any external help. This includes, but is not limited to, calling someone, messaging someone, or searching for information online.
7. The plan must be fully deterministic. You MUST NOT include conditional logic such as “check X, and if Y happens, then do Z.” All steps must proceed directly without branching.
8. You may directly propose a concrete and complete plan without considering whether the required tools or objects are currently available in the environment (but don't use expressions like "existing xxx", simply use the object directly). If any required items are unavailable, the user will clarify in subsequent turns.
9. Definitions of tools/entities that you should list out:
    (1) **Exclude Body Parts**: Do NOT list human body parts (e.g., hands, feet, eyes) as tools or entities.
    (2) **Only Tangible Household Objects**: List only concrete household objects. Do NOT include natural elements or abstract conditions (e.g., sunlight, air, temperature, time, water).
    (3) **Structural Elements Are Implicit**: Floors, walls, ceilings, doors, and other permanent structural parts of the house are always present. Do NOT list them as tools or entities (e.g., Do NOT list "existing walls" as a tool / entity), though you may reference and use them in your plan.
    (4) **Single-Object Constraint**: Every tool or entity must be a single, specific object. You must NOT list multiple alternatives. Do NOT use words such as "or", "and/or", "optional", "etc.", or similar expressions that indicate alternatives or optional items. Each listed tool/entity must be exactly one concrete object.{resample_rule}

Output format:
<answer_start>
- ##Plan X## 
[Used Tools / Entities]: Write a comma-separated list of all tools or entities used in this plan. (**<Tool_1>**, **<Tool_2>**, ...)
[Step description]: Provide numbered steps. Each step must explain what to do, how to use the tools/entities, and in what order.
- ##Plan (X+1)##
... 

where X=1,2,..., corresponding to the number of plans you generate. You may reason before <answer_start>, but once <answer_start> appears, do not output any additional reasoning, commentary, or analysis; output only the final answer.
Now generate {verbal_sample_num} methodologically different plans for:
Question: {Question}
'''

answer_candidate_iterative_sampling_prompt_one = '''
Unfortunately, I don't have enough tools / objects you have mentioned to execute your plan. Specifically, I don't have:
{Used_tools}
Please generate a new plan that does not use any of the above tools. All tool / entity names must be wrapped in ** **.{resample_rule}

Output format:
<answer_start>
[Used Tools / Entities]: Write a comma-separated list of all tools or entities used in this plan, each tool must be wrapped in ** **.
[Step description]: Provide numbered steps. Each step must explain what to do, how to use the tools/entities, and in what order.

You may reason before <answer_start>, but once <answer_start> appears, do not output any additional reasoning, commentary, or analysis; output only the final answer.
Your answer is: '''

answer_candidate_iterative_sampling_prompt = '''
Unfortunately, I don't have enough tools / objects you have mentioned to execute your plan. Specifically, I don't have:
{Used_tools}
Please generate {verbal_sample_num} different step-by-step plans that does not use any of the above tools. All tool / entity names must be wrapped in ** **.

Requirements:
1. Each plan must use a fundamentally different method or strategy, not just swapping tools or objects.
2. The generated plans must be fundamentally different from the original plan instead of just swapping tools or objects.
3. For each step, clearly state which tools or entities are used, how they are used, and the correct order of operations.
4. All tool / entity names must be wrapped in ** **.
5. For every tool incorporated in the plan, you must clearly and concretely state what the tool is. Vague descriptions such as "something hard" or "existing heavy object" are not allowed.
6. You MUST NOT seek any external help. This includes, but is not limited to, calling someone, messaging someone, or searching for information online.
7. The plan must be fully deterministic. You MUST NOT include conditional logic such as “check X, and if Y happens, then do Z.” All steps must proceed directly without branching.
8. You may directly propose a concrete and complete plan without considering whether the required tools or objects are currently available in the environment (but don't use expressions like "existing xxx", simply use the object directly). If any required items are unavailable, the user will clarify in subsequent turns.
9. Definitions of tools/entities that you should list out:
    (1) **Exclude Body Parts**: Do NOT list human body parts (e.g., hands, feet, eyes) as tools or entities.
    (2) **Only Tangible Household Objects**: List only concrete household objects. Do NOT include natural elements or abstract conditions (e.g., sunlight, air, temperature, time, water).
    (3) **Structural Elements Are Implicit**: Floors, walls, ceilings, doors, and other permanent structural parts of the house are always present. Do NOT list them as tools or entities (e.g., Do NOT list "existing walls" as a tool / entity), though you may reference and use them in your plan.
    (4) **Single-Object Constraint**: Every tool or entity must be a single, specific object. You must NOT list multiple alternatives. Do NOT use words such as "or", "and/or", "optional", "etc.", or similar expressions that indicate alternatives or optional items. Each listed tool/entity must be exactly one concrete object.{resample_rule}

Output format for your plan:
<answer_start>
- ##Plan X##
[Used Tools / Entities]: Write a comma-separated list of all tools or entities used in this plan, each tool must be wrapped in ** **. (**<Tool_1>**, **<Tool_2>**, ...)
[Step description]: Provide numbered steps. Each step must explain what to do, how to use the tools/entities, and in what order.
- ##Plan (X+1)##
... 

where X=1,2,..., corresponding to the number of plans you generate. You may reason before <answer_start>, but once <answer_start> appears, do not output any additional reasoning, commentary, or analysis; output only the final answer. Now generate {verbal_sample_num} methodologically different plans:
'''

                   

                                
merge_entity_prompt = '''
You are given a list of tools/entities.

## Task
Deduplicate only items that refer to the SAME concrete object. This is a paraphrase-only / same-object deduplication task.

## Rules
1. You MAY merge exact duplicates, singular/plural variants, article/determiner variants, and modifier variants that still denote the same concrete object.
2. You MAY merge same-head-noun variants when the modifier does not change the object category. Example: "wood knife" and "iron knife" may merge to "knife".
3. You MUST NOT merge different objects. Example: "knife" and "scissors" must stay separate.
4. You MUST NOT merge different categories. Example: "glue" and "tape" must stay separate.
5. You MUST NOT upward-generalize to a broader category or superset. Never output labels such as "sharp tools", "cleaning tools", or "tool" unless that exact semantics is already what the input item means.
6. The output must not introduce a label whose semantics are broader than any merged input.
7. If you are unsure whether two items denote the same object, keep them separate.
8. The final output must be the complete deduplicated list, with each item wrapped in ** **.
9. The output size must be less than or equal to the input size. Only remove true duplicates.

## Examples
- "spoons" and "spoon" -> merge to "spoon"
- "a knife" and "knife" -> merge to "knife"
- "wood knife" and "iron knife" -> merge to "knife"
- "knife" and "scissors" -> do not merge
- "glue" and "tape" -> do not merge
- "knife" and "scissors" -> NEVER merge to "sharp tools"
- "glue" and "tape" -> NEVER merge to "adhesive tools"

## Output format:
<answer_start>
[Used Tools / Entities]: **entity 1**, **entity 2**, **entity 3**

Note that the tools / entities listed after [Used Tools / Entities] should be the complete deduplicated list. The following is the list of tools/entities to be merged:
{Used_tools}

Your answer:
'''

                                            
user_pref_iterative_sampling_prompt_one = '''
Unfortunately, I have the following personal preferences:
{Used_prefs}

These preferences prevent me from carrying out the plans you proposed.  
Please generate a new plan that does NOT violate any of my preferences.

Requirements:
1. The plan must fully respect all listed preferences.
2. For each step, clearly state which tools or entities are used, how they are used, and the correct order of operations.
3. All tool / entity names must be wrapped in ** **.
4. For every tool incorporated in the plan, you must clearly and concretely state what the tool is. Vague descriptions such as "something hard" or "existing heavy object" are not allowed.
5. You MUST NOT seek any external help. This includes, but is not limited to, calling someone, messaging someone, or searching for information online.
6. The plan must be fully deterministic. You MUST NOT include conditional logic such as “check X, and if Y happens, then do Z.” All steps must proceed directly without branching.
7. You may directly propose a concrete and complete plan without considering whether the required tools or objects are currently available in the environment (but don't use expressions like "existing xxx", simply use the object directly). If any required items are unavailable, the user will clarify in subsequent turns.
8. Definitions of tools/entities that you should list out:
    (1) **Exclude Body Parts**: Do NOT list human body parts (e.g., hands, feet, eyes) as tools or entities.
    (2) **Only Tangible Household Objects**: List only concrete household objects. Do NOT include natural elements or abstract conditions (e.g., sunlight, air, temperature, time, water).
    (3) **Structural Elements Are Implicit**: Floors, walls, ceilings, doors, and other permanent structural parts of the house are always present. Do NOT list them as tools or entities (e.g., Do NOT list "existing walls" as a tool / entity), though you may reference and use them in your plan.
    (4) **Single-Object Constraint**: Every tool or entity must be a single, specific object. You must NOT list multiple alternatives. Do NOT use words such as "or", "and/or", "optional", "etc.", or similar expressions that indicate alternatives or optional items. Each listed tool/entity must be exactly one concrete object.{resample_rule}

Output format for your plan:
<answer_start>
[Used Tools / Entities]: Write a comma-separated list of all tools or entities used in this plan, each tool must be wrapped in ** **. (**<Tool_1>**, **<Tool_2>**, ...)
[Step description]: Provide numbered steps. Each step must explain what to do, how to use the tools/entities, and in what order.

You may reason before <answer_start>, but once <answer_start> appears, do not output any additional reasoning, commentary, or analysis; output only the final answer. Your answer is: '''

user_pref_iterative_sampling_prompt = '''
Unfortunately, I have the following personal preferences:
{Used_prefs}
These preferences prevent me from carrying out the plans you proposed.  
Please generate {verbal_sample_num} different step-by-step plans that does NOT violate any of my preferences.

Requirements:
1. Each plan must fully respect all listed preferences.
2. Each plan must use a fundamentally different method or strategy, not just swapping tools or objects.
3. The generated plans must be fundamentally different from the original plan instead of just swapping tools or objects.
4. For each step, clearly state which tools or entities are used, how they are used, and the correct order of operations.
5. All tool / entity names must be wrapped in ** **.
6. For every tool incorporated in the plan, you must clearly and concretely state what the tool is. Vague descriptions such as "something hard" or "existing heavy object" are not allowed.
7. You MUST NOT seek any external help. This includes, but is not limited to, calling someone, messaging someone, or searching for information online.
8. The plan must be fully deterministic. You MUST NOT include conditional logic such as “check X, and if Y happens, then do Z.” All steps must proceed directly without branching.
9. You may directly propose a concrete and complete plan without considering whether the required tools or objects are currently available in the environment (but don't use expressions like "existing xxx", simply use the object directly). If any required items are unavailable, the user will clarify in subsequent turns.
10. Definitions of tools/entities that you should list out:
    (1) **Exclude Body Parts**: Do NOT list human body parts (e.g., hands, feet, eyes) as tools or entities.
    (2) **Only Tangible Household Objects**: List only concrete household objects. Do NOT include natural elements or abstract conditions (e.g., sunlight, air, temperature, time, water).
    (3) **Structural Elements Are Implicit**: Floors, walls, ceilings, doors, and other permanent structural parts of the house are always present. Do NOT list them as tools or entities (e.g., Do NOT list "existing walls" as a tool / entity), though you may reference and use them in your plan.
    (4) **Single-Object Constraint**: Every tool or entity must be a single, specific object. You must NOT list multiple alternatives. Do NOT use words such as "or", "and/or", "optional", "etc.", or similar expressions that indicate alternatives or optional items. Each listed tool/entity must be exactly one concrete object.{resample_rule}

Output format for your plan:
<answer_start>
- ##Plan X##
[Used Tools / Entities]: Write a comma-separated list of all tools or entities used in this plan, each tool must be wrapped in ** **. (**<Tool_1>**, **<Tool_2>**, ...)
[Step description]: Provide numbered steps. Each step must explain what to do, how to use the tools/entities, and in what order.
- ##Plan (X+1)##
... 

where X=1,2,..., corresponding to the number of plans you generate. You may reason before <answer_start>, but once <answer_start> appears, do not output any additional reasoning, commentary, or analysis; output only the final answer. Now generate {verbal_sample_num} methodologically different plans:
'''

                                     
tool_extraction_prompt = '''
You will be given:
1. A rewritten user query
2. A reference solution for the same task
3. A candidate plan

Your task is to extract the concrete tools / entities that the candidate plan actually uses or clearly relies on, while avoiding items that would break task solvability if banned later.

## Extraction Rules
1. Extract only tangible tools / entities that are explicitly used or clearly required by the candidate plan.
2. Do NOT extract human body parts, natural elements, environmental conditions, or permanent structural parts of a house.
3. Do NOT extract vague placeholders such as "heavy object", "something sharp", or "any container".
4. Do NOT extract an item if it is already explicitly required by the rewritten query.
5. Do NOT extract an item if it is explicitly used, required, or clearly indispensable in the reference solution.
6. Prefer concrete object names that are suitable for later verification.
7. If nothing valid remains after applying the rules above, output an empty list.

## Output format
<answer_start>
[Used Tools / Entities]: **tool/entity 1**, **tool/entity 2**, **tool/entity 3**

Only output the final answer after <answer_start>.

Rewritten Query:
{Question}

Reference Solution:
{Reference_solution}

Candidate Plan:
{Plan}

Your answer:
'''

user_preference_induction_prompt = '''
You will be given:
1. A rewritten user query
2. A reference solution for the same task
3. A candidate plan
4. The tools / entities extracted from that candidate plan

Your task is to infer realistic user preferences that could explain why the user would reject the candidate plan.

## Core idea
Each preference should stay grounded in the candidate plan, but it should usually be broader than banning one exact object from one exact step.

Ground the preference in one of the following:
- a **tool attribute**: a property of the tool / entity itself, such as being sharp, powdery, fragile, hot, rigid, heavy, strongly scented, absorbent, or messy to use
- a **usage pattern**: a recurring way the tool / entity is used, such as directly spraying liquid onto a surface, forceful prying, repeated pounding against a hard surface, direct pouring, prolonged direct airflow, or hard-to-control scraping
- only if neither of the above is natural or reasonable, a broader **tool category**

The final output should be a realistic human preference, not a world constraint and not a positive endorsement of the plan.

## Requirements
1. Each preference must clearly block at least one step in the candidate plan, and a later judge must be able to tell whether a new plan violates it.
1a. Each output item must express exactly one core restriction. If the candidate plan supports several objections, output several separate **...** preferences instead of combining them in one sentence or one bold item.
1b. Do NOT write one preference that contains multiple first-person restrictions separated by commas, semicolons, or repeated phrases like **I do not want...**, **I don't want...**, or **I avoid...**.
2. Prefer a preference that blocks a meaningful family of similar plans, not just this one exact object mention, as long as the broader wording still sounds natural and reasonable for a real person.
3. First try to express the objection as a disliked usage pattern or a disliked tool attribute. If that broader wording would sound unnatural or unreasonable, fall back to a narrower tool category preference.
4. Usually broaden somewhat beyond this exact query instance when that preserves the meaning, but do not broaden so much that the preference becomes vague, unrealistic, or hard to judge.
5. If the disliked part is mainly a usage pattern, do NOT unnecessarily mention the specific target object from this query (for example, do not tie it to **carpets**, **fabrics**, **stains**, or other query-specific recipients unless that object is truly necessary to define the preference).
5a. If the plan uses a support object, helper object, container, barrier, towel, card, cup, bowl, lid, hanger, clip, or other incidental household item, do NOT name that exact object unless it is clearly central. Prefer to express the real objection using its relevant attribute or functional role, such as **fragile container**, **lint-shedding absorbent material**, **sticky material**, **fine-mesh filtering tool**, **rigid barrier tool**, **slippery hanging support**, **flimsy heat-trapping barrier**, or **heavy rigid object**.
6. Do NOT output bare vague labels such as **slow**, **too long**, **messy**, **hard**, **inconvenient**, **impractical**, or **unnecessary** as standalone preferences.
7. Do NOT output generic style/personality statements such as **enjoys efficient, step-by-step approaches** or **enjoys DIY solutions**.
8. Do NOT output positive requests such as **I like using...**, **I want to use...**, or **I prefer to use...**.
9. Do NOT use category-by-example wording such as **tools like X**, **utensils such as Y**, or **for example** inside the final preference. Name the attribute, usage pattern, or category directly.
10. If a natural reason is available, you may include one short reason. The reason should be brief and should clarify the preference rather than expand its scope.
10a. A good reason should point to a concrete mechanism or risk, such as residue, lint, splashing, clogging, scratching, tearing, slipping, contamination, instability, trapped moisture, breakage, overheating, staining, or difficult cleanup. Do NOT use a vague reason like **it seems impractical**, **it feels unnecessary**, or **I just do not like it** unless you can rewrite it into a grounded concrete concern.
11. If the reason would be long, vague, awkward, or hard to justify naturally, omit it instead of forcing one.
12. Do NOT output anything that would invalidate the reference solution or that is already explicitly required by the rewritten query.{resample_prefs_rule}
12a. Do NOT output meta-level preferences about the assistant response, plan format, refusal behavior, task assumptions, or whether a method is "workable" or "actionable" (for example, **I do not want a response that refuses...**, **I do not want a plan that assumes...**, or **I do not want instructions that...**). A valid preference should restrict a physical tool attribute, material property, usage pattern, or tool category. If a meta objection cannot be rewritten into a physical restriction, omit it.
13. Only use an exact-object ban when a broader attribute-, usage-pattern-, or category-level preference would sound unnatural or unreasonable.
14. If you cannot infer a realistic and stable broader preference with enough support from the plan, omit it rather than guessing.
15. Avoid making every preference use the exact same sentence template. Light variation is welcome when it remains clear, natural, and judgeable, but do not force stylistic diversity at the cost of clarity.
16. It is fine to output multiple preferences when the candidate plan supports multiple genuinely different objections. Coverage is important: keep all grounded, non-redundant objection families that are well supported by the plan.
17. A preference that still names one exact household object should be rare. If replacing that object with another object of the same relevant attribute or the same usage pattern would preserve the user's objection, rewrite the preference at that broader level instead of naming the exact object.
18. Each final preference must be a complete natural first-person sentence. Avoid fragments such as **avoid using...**, third-person narration such as **Wants to avoid...**, or awkward gerund phrases such as **Not wanting to use...**.
19. Do NOT stop after one or two preferences if the plan clearly contains additional distinct grounded objections. For a non-trivial plan, it is often appropriate to output several preferences, and coverage is more important than keeping the list artificially short.
20. If several concrete steps express the same deeper objection, merge them into one broader preference. But if they express genuinely different objection families, keep them separate even if they share a broad concern such as residue, moisture, slowness, instability, or difficult cleanup.
21. Prefer a rich set of broad grounded preferences over a tiny set that misses many plausible objections, but avoid an overly fragmented list that repeats the same core restriction in slightly different words.
22. Atomicity is important: one preference can have one short reason, but it should not bundle multiple unrelated concerns. For example, do not combine **direct spraying**, **strong scents**, and **adhesive residue** in one preference; output them as separate preferences if all are supported by the plan.

## How to think before writing
- Look at each extracted tool / entity and ask: is the real objection to a property of the tool itself, such as being sharp, powdery, rigid, hot, fragile, or messy to use?
- Then look at each distinct way the tool is used in the candidate plan and ask: is the real objection to a recurring usage pattern, such as spraying directly, pouring directly, scraping rigidly, prying forcefully, pounding repeatedly, or relying on prolonged airflow?
- If a broader wording at the level of a tool attribute or usage pattern sounds like something a real person could naturally say, prefer that broader wording over an exact object ban.
- If that broader wording would sound unnatural, unreasonable, or too abstract, fall back to a narrower tool-category preference instead of forcing the broad phrasing.
- Only if neither a tool attribute, a usage pattern, nor a reasonable tool category yields a natural and judgeable preference should you consider an exact-object ban.
- Ignore objections that are only about the answer being unhelpful, refusing, choosing a wrong premise, asking the user to relax constraints, or switching tasks. Those are plan-quality failures, not user preferences, unless you can rewrite them as a concrete physical restriction on tools, materials, or operations.
- Tool-side reasons may come from things like sharpness, powder/dust, smell, residue, heat, fragility, contamination, wastefulness, or hygiene concerns.
- Usage-side reasons may come from things like needing force, repeated rubbing, direct pouring, direct spraying, prolonged waiting, prolonged airflow, hard-to-control application, or messy transfer.
- For helper objects and support objects, prefer to describe the relevant property or role rather than the household object name itself whenever that broader wording is still natural.
- If the exact object mainly serves as a **container**, **barrier**, **filter**, **absorbent**, **backing surface**, **hanging support**, **gripping layer**, or **transfer medium**, rewrite the preference around that role or its key property instead of around the household object name.
- For example, prefer **lint-shedding absorbent paper materials** over **paper towels**, **fragile or food-use containers for mixing or transferring cleaning liquids** over **drinking cup** or **glass measuring cup**, **fine-mesh filtering tools** over **sieve**, **unstable hanging supports** over **plastic hanger** or **rod**, and **flimsy heat-trapping barriers** over **aluminum foil** or **plastic wrap**, as long as the broader wording stays natural and judgeable.
- When you output multiple preferences, try to make the core restriction different across them. Different preferences should ideally ban different tool attributes, different usage patterns, or different tool categories.
- Do NOT produce multiple preferences that mainly ban the same core behavior with only slightly different reasons.
- Do NOT pack multiple objection families into one bold item. If you catch yourself writing a second **I do not want...**, **I don't want...**, or **I avoid...** inside the same preference, split it into a separate preference.
- Broadening one preference should NOT make you stop extracting other distinct grounded objection families elsewhere in the plan. A single plan can naturally support many preferences if it uses different risky materials, different force or motion patterns, different heat or moisture patterns, and different helper-object roles.
- Do NOT collapse two preferences merely because they both involve residue, moisture, slowness, instability, or inconvenience. If they forbid different grounded mechanisms, keep them separate.
- Before finalizing a preference, ask yourself: if the candidate plan swapped this exact tool for a different tool with the same relevant property or the same usage pattern, would this preference still naturally make sense? If yes, rewrite it at that broader level.
- Do not turn every concrete detail into its own preference. Instead, cluster concrete details into broader objection families and keep all well-supported, non-redundant families.
- Before finalizing, ask whether you have covered the main distinct objections in the plan. If not, add the missing grounded objection families.

## Short examples
Bad: **slow**
Good: **I do not want to rely on prolonged direct airflow for drying, because it feels too slow.**

Bad: **I do not want to use a knife for this.**
Good: **I do not want to use sharp things, because I am worried about getting cut.**

Bad: **I do not want to use flour for this.**
Good: **I do not want to use powdery or dust-form substances, because I am concerned about airborne residue or irritation.**

Bad: **I do not want to use baking soda to clean this stain.**
Bad: **I do not want to sprinkle powder-based substances directly onto carpets or fabrics.**
Good: **I do not want to sprinkle powder-based substances directly onto surfaces, because I do not want residue to spread.**

Bad: **I do not want to use utensils like butter knives to spread cleaning products.**
Good: **I do not want to spread cleaning products with rigid scraping tools, because I am concerned about scratching the surface.**

Bad: **I do not want to use a crowbar to open things.**
Good: **I do not want to use forceful prying motions, because I am concerned the object may jerk loose and cause injury.**

Bad: **I do not want to spray liquids directly onto surfaces, because of overspray, I do not want to use strong-smelling cleaners, because of fumes, I avoid adhesive pickup tools, because they can leave residue.**
Good:
**I do not want to spray liquids directly onto surfaces, because overspray can spread beyond the target area.**
**I do not want to use strong-smelling cleaners indoors, because I am concerned about fumes.**
**I do not want to use adhesive pickup materials, because they can leave residue.**

Bad: **I do not want to use a hair dryer here.**
Good: **I do not want to rely on prolonged direct airflow, because it feels too harsh and hard to control.**

Bad: **I do not want to use a spray bottle on the carpet.**
Good: **I do not want to spray liquid directly onto a surface, because I am concerned about over-saturation.**

Bad: **I do not want to use adhesive tape on carpet fibers.**
Good: **I do not want to use sticky or adhesive materials on fibrous surfaces, because I am concerned about residue being left behind.**

Bad: **I do not want to use paper towels for absorbing liquids.**
Good: **I do not want to use lint-shedding absorbent paper materials on soft surfaces, because I am concerned about fibers being left behind.**

Bad: **I do not want to scoop hot water out of a pot with a glass measuring cup.**
Good: **I do not want to transfer boiling liquid through fragile containers, because I am concerned about cracks, splashing, or loss of control.**

Bad: **I do not want to use a drinking cup as a mixing container for cleaning solutions.**
Good: **I do not want to mix cleaning solutions in food-use containers, because I am concerned about contamination or cleanup problems.**

Bad: **I do not want to use a fine-mesh sieve in a cleaning process.**
Good: **I do not want to rely on fine-mesh filtering tools to strain a cleaning mixture, because residue can clog them and make cleanup difficult.**

Bad: **I do not want to use aluminum foil for heat insulation.**
Good: **I do not want to rely on flimsy heat-trapping barriers, because I am concerned about tearing, slipping, or poor control.**

Bad: **I do not want to use hydrogen peroxide on home carpets, due to concerns about bleaching or discoloration.**
Good: **I do not want to use bleaching or oxidizing liquids on soft surfaces, because I am concerned about discoloration.**

Bad: **I do not want to use a vacuum cleaner for this task.**
Good: **I do not want to rely on strong suction to retrieve small objects from tight spaces, because it feels too forceful and unreliable.**

Bad: **I do not want to use a shower curtain rod as a hanging point for clothing.**
Good: **I do not want to hang clothing from unstable fixtures, because I am worried they are not designed to support the weight.**

Bad: **I do not want to use ice in direct contact with the stain.**
Good: **I do not want to put melting or very cold items directly onto a stain, because I am concerned about spreading moisture.**

Bad: **I do not want to use a clothes dryer to remove wrinkles from garments.**
Good: **I do not want to use heated tumbling methods for wrinkle removal, because they feel too harsh on delicate fabric.**

Bad: **I avoid cleaning methods that require waiting for an extended period before completing the process.**
Good: **I avoid cleaning methods that require leaving residue on a surface before removal.**

Bad: **I do not want to use spray bottles to apply liquids to carpets.**
Good: **I do not want to spray liquids directly onto a surface, because I am concerned about over-saturation.**

Bad pair:
- **I do not want to sprinkle powder-based substances directly onto surfaces, because I am concerned about residue being left behind.**
- **I avoid cleaning methods that require leaving residue on a surface before removal, as I prefer immediate cleanup.**

Better pair:
- **I do not want to sprinkle powder-based substances directly onto surfaces, because I am concerned about residue being left behind.**
- **I do not want to pour liquids directly onto a surface, because I am concerned about over-saturation.**

Good richer set:
- **I do not want to sprinkle powder-based substances directly onto surfaces, because I am concerned about residue being left behind.**
- **I do not want to apply liquids directly onto a soft surface, because I am concerned about over-saturation.**
- **I do not want to use sticky or adhesive materials on fibrous surfaces, because I am concerned about residue being left behind.**

These should stay separate because they forbid different grounded objection families.

Also keep these separate when supported by the plan:
- **I do not want to sprinkle powder-based substances directly onto surfaces, because I am concerned about residue being left behind.**
- **I do not want to rely on prolonged direct airflow for drying, because it feels too slow and hard to control.**
- **I do not want to use sticky or adhesive materials on fibrous surfaces, because I am concerned about residue being left behind.**
- **I do not want to use bleaching or oxidizing liquids on soft surfaces, because I am concerned about discoloration.**

Even though all four involve cleanup or surface concerns, they forbid different grounded mechanisms and should not be collapsed into one vague preference.

Natural broadening:
- Candidate plan uses a **knife** to scrape or cut.
  Better preference: **I do not want to use sharp things, because I am worried about getting cut.**
- Candidate plan uses a **spray bottle** to wet a surface.
  Better preference: **I do not want to spray liquid directly onto a surface, because I am concerned about over-saturation.**
- Candidate plan uses a **mallet** to strike something on a countertop.
  Better preference: **I do not want to pound things repeatedly against a hard surface, because I am worried about damaging it.**

When broader wording is unnatural or unreasonable:
- If a strange object appears in the plan and there is no believable broader attribute or usage-pattern dislike, a narrower tool-category preference is acceptable.
- Do not force a broad abstraction just because it seems more general.

## Guidance
- Keep the wording human and natural, but do not make the preference sound like a plain exact-object ban when a clearer broader preference is available.
- Make every final preference a complete first-person sentence that can stand on its own.
- Keep the avoided behavior clear and judgeable.
- When the issue is a way of using the tool, describe the avoided usage pattern itself, not the query-specific object it happens to be used on here.
- For tool-grounded preferences, ask yourself whether the real objection is to a property of the tool, a property of the usage, or only then to the tool category itself. Prefer tool properties and usage properties when they sound natural and reasonable.
- If two candidate preferences feel like one is just a narrower object-specific version of the other broader restriction, keep the broader one and drop the narrow one.
- Try to cover different plausible dislike angles across the extracted tools and usages, instead of repeating the same concern in several phrasings or reusing the same sentence frame every time.
- If the only inference is a vague reason, turn it into a clearer avoided behavior or omit it.
- If the evidence only weakly supports a preference, omit it instead of inventing a shaky broad ban.

Output format:
<answer_start>
- [User prefs]: User preferences separated by commas, each wrapped with ** (**<preference_1>**, ...).

Rewritten Query: {Question}
Reference Solution: {Reference_solution}
Extracted Tools / Entities: {Extracted_tools}
Candidate Plan: {Plan}
You may reason before <answer_start>, but once <answer_start> appears, do not output any additional reasoning, commentary, or analysis; output only the final answer. Your answer is: '''

resample_prefs_rule = '''\n\t(Important) Do not generate user preferences that would conflict with or invalidate the following plan: {gt_content}'''

                                  
                                                                                                                                                                                                                                                                                                                          
merge_user_prefs_prompt = '''
You are given a list of user preferences.

## Task
Merge ONLY preferences that forbid the SAME core restriction. This is a true-paraphrase / same-restriction deduplication task.

## Rules
1. In the output, each final preference must be wrapped in ** **.
2. You MAY merge preferences only when they forbid the same core restriction: the same tool, the same tool attribute, or the same tool-usage pattern.
3. You MAY choose one cleaner phrasing for true paraphrases, but you MUST NOT broaden the scope.
4. You MUST NOT merge preferences merely because they are on the same topic, in the same activity family, or motivated by the same concern.
5. You MUST NOT turn a specific ban into a broader attribute/category ban during merge.
6. You MUST NOT rewrite the output into something that would forbid more plans than any single input already forbids.
7. If two preferences involve different forbidden tools, different attributes, or different usage patterns, keep them separate.
8. Attribute-level preferences should be created during induction, not invented during merge.
9. If you are unsure whether two inputs express the same restriction, keep them separate.
10. The final output must be the complete deduplicated list.

## Examples:
- Merge: "I do not want to use a knife." and "I do not want to use knives." -> keep one cleaner phrasing.
- Merge: two phrasings that both forbid direct spraying of liquid onto a surface -> keep one cleaner phrasing.
- Do not merge: "I do not want to use baking soda to clean stains" and "I do not want to sprinkle powder onto fabric."
- Do not merge: "I do not want to use spray bottles on carpets" and "I do not want to spray liquids onto surfaces."
- Do not merge: "I do not want to use sharp blades" and "I do not want to use knives" unless they are clearly the same restriction in context.
- Forbidden rewrite: never turn several specific inputs into a broader new restriction that none of them alone states.

## Output format:
<answer_start>
- [User prefs]: **user_pref_1**, **user_pref_2**, **user_pref_3**

Note that the user preferences listed after [User prefs] should be the complete deduplicated list. The following is the list of user preferences to merge:
{Used_prefs}

Your answer:
'''

                      

                                                   
judge_by_env_cons_prompt = '''## Task:
Check whether the proposed plan to the question violates ANY environment constraints.

## Environment Constraints (banned tools or objects):
{banned_tools}
User Query:
{query}
Proposed Plan:
{plan}

## Rules:
- If the plan uses, requires, or relies on ANY banned tool/object, it is a violation.
- Even indirect, implied, or required usage counts.
- Treat banned tools/objects category-strictly: if a banned item is a broader category, then any subtype, variant, modifier form, or specific instance of that category also counts as banned.
- For example, if "knife" is banned, then "wood knife", "iron knife", "kitchen knife", and "butter knife" all count as violations.
- Do not rely on exact string matching only. Judge by object identity, subtype relation, and common-sense category membership.

## Output format:
<answer_start>:
- [Result]: **YES** / **NO**
- [Details]: 
The plan uses the following banned tools/objects:
1. ##<tool/object 1>##
2. ...

## Guidelines:
1. **YES** indicates a violation; **NO** indicates no violation.
2. The Result (**YES** / **NO**) must be wrapped in double asterisks (** **).
3. Any violated and banned tools or objects must be wrapped in double hash marks (## ##).
4. If there are no violations, the Details section may be left empty.
5. You may reason before <answer_start>, but once <answer_start> appears, do not output any additional reasoning, commentary, or analysis; output only the final answer.

## Examples:
- If the banned tool is "knife", a plan using a "butter knife" is still a violation.
- If the banned tool is "knife", a plan using "scissors" is not automatically a violation unless scissors are also banned.

Your answer:
'''

                                                    
judge_by_user_prefs_prompt = '''## Task
Check whether the proposed plan to the question violates ANY user preferences.
User Preferences:
{user_prefs}
User Query:
{query}
Proposed Plan:
{plan}

## Rules:
- If the plan conflicts with ANY user preference, it is a violation.
- Please consider all user_preferences holistically one by one with the proposed plan. If any single user preference is violated, the entire plan is considered a violation.
- Judge by meaning, not exact string overlap.
- If a preference forbids a **tool attribute**, then using any concrete tool/object with that attribute counts as a violation.
- If a preference forbids a **usage pattern**, then any equivalent usage pattern counts as a violation even if the exact tool name differs.
- If a preference is broader than the exact object named in the plan, still apply the broader meaning faithfully.

## Output format:
<answer_start>:
- [Result]: **YES** / **NO**
- [Details]:
The plan violates the following user preferences:
1. ##<preference 1>##
2. ...

## Guidelines:
1. **YES** indicates a violation; **NO** indicates no violation.
2. The Result (**YES** / **NO**) must be wrapped in double asterisks (** **).
3. Any violated user preferences must be wrapped in double hash marks (## ##).
4. If there are no violations, the Details section may be left empty.
5. You may reason before <answer_start>, but once <answer_start> appears, do not output any additional reasoning, commentary, or analysis; output only the final answer.
6. Examples:
   - If the preference says the user wants to avoid **sharp things**, then using a **knife**, **razor**, or another sharp object is a violation.
   - If the preference says the user wants to avoid **spraying liquid directly onto a surface**, then using any tool to directly spray liquid onto a surface is a violation.

Your answer:
'''

                                            
judge_by_rubrics_prompt = '''You are a strict evaluator.
## Task:
Evaluate whether the proposed plan is acceptable according to ALL rubrics.

## Rubrics:
1. **Tool-use feasibility**: Could the tools / objects be realistically used in the way described in the plan? Consider common-sense knowledge about the tools / objects.
2. **Physical possibility**: When the tool/object is used as planned, will it have the environmental impact as described in the plan? Consider the laws of physics and the real world.
3. **Effectiveness**: If the plan is executed as described, will it accomplish the task in the question? Consider whether the steps logically lead to the successful completion of the task.
4. **Logical step ordering**: If there are sequential steps, are they in a logical order that would work in practice? Consider whether the sequence of actions makes sense and is likely to be effective.
5. **Safety**: Does the plan involve any actions that could cause harm or damage to people, property, or the environment? Consider both direct and indirect consequences.
6. **Autonomy**: Does the plan rely on any external help, such as asking other people for help, calling someone, or using outside services? Consider whether the plan can be executed independently by the agent.

User Query:
{query}
Proposed Plan:
{plan}

## Rules:
- If the plan fails ANY rubric, it is NOT acceptable.
- Be conservative and realistic.

## Output format:
<answer_start>:
- [Result]: **PASS** / **FAIL**
- [Failed Rubrics]:
1. ##<rubric_name_1>##
2. ##<rubric_name_2>##
3. ...
- [Reason]: 
1. For ##<rubric_name_1>##: <reason for failure of rubric 1>
2. For ##<rubric_name_2>##: <reason for failure of rubric 2>
3. ...

## Guidelines:
1. **PASS** means the plan passes all rubrics; **FAIL** means at least one rubric fails.
2. The Result (**PASS** / **FAIL**) must be wrapped in double asterisks (** **).
3. Any failed rubric names must be wrapped in double hash marks (## ##).
4. If all rubrics pass, the [Failed Rubrics] and [Reason] sections may be left empty.
5. You may include reasoning before <answer_start>, but once <answer_start> is given, it will be treated as your final answer.
6. When outputting the rubric names, you must use the exact wording provided above without any modification. Do not alter, paraphrase, abbreviate, or reformat the rubric names in any way.
Your answer:
'''

                     

                                       
generate_user_feedback_prompt = '''You are a user giving feedback to improve a plan.
User Query:
{query}
Proposed Plan:
{plan}
Judge Feedback:
{judge_feedback}

## Task:
Simulate a realistic user response pointing out what is wrong with the plan according to the judge feedback, and ask the assistant to regenerate the plan.

## Required Output Format for the regenerated plan:
<answer_start>
[Used Tools / Entities]: Write a comma-separated list of all tools or entities used in this plan. (**<Tool_1>**, **<Tool_2>**, ...)Each tool/entity must be wrapped in ** **.
[Step description]: Provide numbered steps. Each step must explain what to do, how to use the tools/entities, and in what order.

## Guidelines:
1. You MUST request the assistant to regenerate the plan using the exact required plan format above.
2. Meaning of the ``<answer_start>`` tag: You should ask the agent to provide the final answer after <answer_start>. Once the agent outputs <answer_start>, everything that follows must be the final answer only.
3. Do NOT introduce new issues not mentioned in judge feedback.
4. Do NOT give suggestions about how to fix the plan.
5. Mention banned tools, violated preferences, or failed rubrics if provided.

Only output the simulated user response without any other text. Your answer:
'''

Judge_feedback_pattern_env_constraints = '''
The model make mistakes on violating environment constraints. Specifically, the model used the following banned tools/objects in the plan:
{banned_tools_used}
'''

Judge_feedback_pattern_user_prefs = '''The model make mistakes on violating user preferences. Specifically, the model violated the following user preferences in the plan:
{user_prefs_violated}
'''

Judge_feedback_pattern_rubrics = '''The model make mistakes on the following rubrics:
{rubrics_failed_with_reason}
'''

                                                             
check_cons_prefs_prompt = '''## Task
Your task is to check whether the following list of tools / objects and the list of user preferences satisfy the criteria below, and filter out any items that do not meet the criteria.

## Criteria:
1. For tools / objects:
(1) They must NOT be human body parts (e.g., hands, feet, eyes).
(2) Natural elements or environmental conditions (e.g., sunlight, air, temperature, time, water) must NOT appear.
(3) Permanent structural parts of a house must NOT be listed as tools or entities (e.g., floors, walls, ceilings, doors).
(4) Vague or non-specific references must NOT be included (e.g., “heavy object”, “existing object”, “any container”).
(5) If a candidate tool/object is already explicitly required by the query or by the planned solution, it must be filtered out.
(6) Do not filter conservatively. If you are unsure, keep the item.
2. For user preferences:
(1) They must be clear enough that a future judge could reliably determine whether a plan violates them.
(2) Bare vague or purely subjective labels such as “slow”, “too long”, “messy”, “annoying”, or “inconvenient” must be filtered out when they are used as the core preference itself. However, such wording may appear in the reason part of a preference if the final forbidden behavior is still clear and violation-checkable.
(3) Do NOT filter a preference merely because it mentions a specific tool or a specific method. Filter it only when it is essentially just a one-off object ban or one-off method ban, without expressing a stable and judgeable tool attribute or tool-usage pattern.
(4) Preferences that forbid a broader tool attribute or usage attribute, such as “I do not want to use sharp tools” or “I avoid directly spraying liquids onto surfaces,” may be kept. Do NOT filter them merely because they still refer to tools or methods.
(5) Preferences that simply ban one exact household object or one overly specific material/object instance, without expressing the broader attribute or usage-pattern preference, should be filtered out.
(6) Preferences that use vague duration wording such as “extended period”, “too long”, or similar wording as the core restriction should be filtered out, unless they are rewritten into a concrete and judgeable process pattern. Such wording may still appear in the reason part if the final forbidden behavior remains clear.
(7) Preferences that are true duplicates must be filtered out.
(8) When deciding whether two preferences are duplicates, focus only on the core restriction: what tool, tool attribute, or tool-usage pattern is being forbidden. Do NOT treat two preferences as duplicates merely because they belong to the same broad activity family, such as steaming, drying, hanging, pressing, cleaning, or wrinkle removal.
(9) Do NOT filter two preferences merely because their reasons are similar. Similar concerns such as residue, smell, safety, inconvenience, waste, or over-saturation are NOT enough by themselves to make two preferences duplicates.
(10) Preferences that are jointly exhaustive with the remaining preference set should be filtered out only when, taken together, they would eliminate nearly every reasonable way of solving the task rather than expressing a small number of realistic dislikes. Apply this criterion sparingly.
(11) Preferences that are already explicitly required by the query, or that would make the planned solution impossible or invalid to execute, must be filtered out.
(12) Filter out user preferences that are clearly unrealistic, unnatural, or implausible as real human preferences in ordinary life, even if they are grammatically valid.
(13) If a preference depends on a vague reason, keep it only when the final wording is still clear and violation-checkable at the plan level.
(14) Be conservative about filtering user preferences. If a preference is realistic, clear, and forbids a distinct behavior, prefer to keep it.
{resample_check_rule}
List of tools / objects to check:
{banned_tools_to_check}
List of user preferences to check:
{user_prefs_to_check}

## Output format:
<answer_start>:
- [Tools/objects to filter out]: **<tool_number_1>**, **<tool_number_2>**, ...
- [User preferences to filter out]: **<pref_number_1>**, **<pref_number_2>**, ...
Where *_number_i (*=tool/pref,i=1,2,...) is the number corresponding to the items that should be filtered out. Only give your final answer after <answer_start>. Your answer is:
'''

resample_check_rule = '''
2. Compatibility with the planned solution:
You are given a planned solution for the same household problem.
(1) Tools / objects:
- The candidate list of tools / objects MUST NOT contain any tool or object that is explicitly used, required, or mentioned in the planned solution. Only filter a candidate tool/object if it is the same item as, or a clear subtype/variant of, an item explicitly used in the planned solution. Do NOT filter items merely because they could also help solve the same problem by a different method.
- The candidate list of tools / objects MUST NOT appear in the following query: {query}. If an item clearly appears in the query, it should be filtered out.
(2) User preferences:
- The candidate list of user preferences MUST NOT contain any preference that is already directly assumed, required, or instantiated by the planned solution at the level of the same tool, the same tool attribute, or the same tool-usage pattern.
- The candidate list of user preferences MUST NOT contain any preference that would make the planned solution impossible or invalid to execute.
- Only filter a user preference when the planned solution already relies on the same core restriction being rejected, or when keeping the preference would make the planned solution logically impossible to execute.
- Do NOT filter a user preference merely because it is broadly related to the same task, the same general activity family, or the same overall domain as the planned solution.
- If the planned solution and the preference involve different tools, different attributes, or different usage patterns, keep the preference unless there is a direct logical conflict.

Planned solution: {planned_solution}\n
'''

'''
(4) If a candidate tool/object is a subtype, modifier form, or specific instance of a broader object that already appears in the query or the planned solution, it must be filtered out.
Examples:
- If the query or planned solution already contains "knife", then "wood knife", "kitchen knife", and "metal knife" must all be filtered out.
(5) If multiple candidate tools/objects are merely different variants of the same underlying object category, prefer filtering out the narrower variants and keeping only the most general natural category-level item when appropriate.
Examples:
- If the candidates are "wood knife", "metal knife", and "knife", keep "knife" and filter out the other two.
- Do not generalize too far: for example, merge knife variants into "knife", not into "tool".
'''

                               

macgyver_adapter_gt_prompt = """
You are converting an existing reference solution into the repository's standard ground-truth plan format.

## Task
You will be given:
1. A user query
2. An original reference solution

Your job is to rewrite the original reference solution into a clean, executable, and standardized ground-truth plan.

## Important Goal
Preserve the core strategy, key actions, and key tools/entities from the original reference solution.
Do NOT invent a different solution.
Do NOT optimize it into a new approach.
Do NOT remove unconventional tool use if it is part of the original solution.
Only standardize, clarify, and structure the solution.

## Input
User Query:
{query}

Original Reference Solution:
{ori_sol}

## Output Format
You MUST output exactly the following structure:

<answer_start>
[Used Tools / Entities]: **tool/entity 1**, **tool/entity 2**, **tool/entity 3**
[Step description]:
1. ...
2. ...
3. ...

## Hard Requirements
1. Output exactly one `<answer_start>` block.
2. Output exactly one `[Used Tools / Entities]` line.
3. Every tool or entity on that line must be wrapped in `** **`.
4. Output exactly one `[Step description]:` section.
5. The step section must be a numbered list starting from `1.`.
6. Every step must be concrete and executable.
7. Keep the plan faithful to the original reference solution.
8. If the original solution is brief, you may add only the minimum missing detail needed to make the same solution executable.
9. Do NOT introduce a different strategy, goal, or tool that changes the original solution.
10. Do NOT include explanations, notes, comments, warnings, or alternatives outside the required format.
11. Do NOT mention these instructions.
12. Definitions of tools/objects that you should list out:
    (1) **Exclude Body Parts**: DO NOT list human body parts (e.g., hands, feet, eyes) as tools or entities.
    (2) **Only Tangible Household Objects**: List only concrete household objects. Do NOT include natural elements or abstract conditions (e.g., sunlight, air, temperature, time, water).
    (3) **Structural Elements Are Implicit**: Floors, walls, ceilings, doors, and other permanent structural parts of the house are always present. Do NOT list them as tools or entities (e.g., Do NOT list "existing walls" as a tool / entity), though you may reference and use them in your plan.
    (4) **Single-Object Constraint**: Every tool or entity must be a single, specific object. You must NOT list multiple alternatives. Do NOT use words such as "or", "and/or", "optional", "etc.", or similar expressions that indicate alternatives or optional items. Each listed tool/entity must be exactly **one concrete** object.

## Additional Guidance
- The `[Used Tools / Entities]` line should list all tools, objects, or materials actually used in the plan.
- If a tool/entity appears in the steps, it should also appear in `[Used Tools / Entities]`.
- Prefer specific physical objects/entities over vague phrases when possible.
- The steps should describe what to do, how the listed tools/entities are used, and the order of actions.
- Keep the plan concise but complete enough to execute.

## Forbidden Errors
- Do not output bullet points instead of numbered steps.
- Do not omit `[Used Tools / Entities]`.
- Do not leave tools unwrapped by `**`.
- Do not output multiple plans.
- Do not output any text before or after the required block.

Your answer:
"""

                          
gt_ext_prefs = '''You will be given a user question and a proposed plan. Your task is to infer realistic human **soft preferences** that could explain why a person would choose THIS plan. Soft preferences are NOT hard constraints. They are plausible habits, dislikes, values, or limitations.

## How to Infer Preferences

Infer preferences in TWO ways:
1. From what the plan AVOIDS: Compare with common alternative solutions. If a normal method was not used, infer why.

Example:
Question: How can I open a stuck metal jar lid?
Plan:
1. Wrap the jar in a towel and hold it between your knees.
2. Put a rubber band around the lid for grip.
3. Slowly twist until it loosens.

Common alternatives NOT used:
- Put the lid in hot water
- Tap the lid with a knife
- Hit it with a hammer

Inferred Preferences:
- **avoids handling very hot water**
- **does not want to use sharp tools**
- **afraid of breaking the jar**
- **may have limited grip strength**

Idea:
Because the plan avoided heat, sharp tools, and brute force,
we infer preferences that explain those choices.

2. From what the plan EMPHASIZES
Look at unusual tools, clever tricks, or special behaviors.
Ask: what kind of person would naturally prefer this style?

Example:
Question: How can I open a tight jar lid?

Plan:
1. Put the jar inside a backpack to stabilize it.
2. Slide a coin under the lid rim to break the seal.
3. Use a door hinge to hold the lid while twisting the jar.

Inferred Preferences:
- **prefers clever leverage tricks over brute force**
- **enjoys mechanical problem-solving hacks**
- **likes using household objects creatively**
- **tries to avoid buying special tools**
- **wants to minimize physical effort**

Idea:
The plan emphasizes creative leverage and unusual tools,
so we infer preferences about ingenuity and low-effort methods.

Both kinds of inference are equally important.

## Rules

- Preferences must be realistic for normal humans
- Do NOT invent absurd or extreme reasons
- Do NOT repeat similar preferences
- Each preference must be short and specific

## Output Format

Each preference must be wrapped in double asterisks.
Example:
<answer_start>
- **avoids touching very hot objects**
- **prefers clever tricks instead of brute force**

## Input
Question:
{question}
Plan:
{plan}
You may reason before <answer_start>, but once <answer_start> appears, do not output any additional reasoning, commentary, or analysis; output only the final answer. Your answer is: '''

                                  
gt_sampling_prompt = '''
You are now in a housing environment. Given the question: {Question}, generate a step-by-step plans to accomplish the task. The environment has strict constraints and user preferences. You MUST generate a plan that does NOT violate any environment constraints or user preferences.

Tools / objects that are NOT allowed to be used (environment constraints):
{banned_tools}env/construction/prompts.py

User preferences that must be respected:
{user_prefs}

Requirements:
1. All tool / entity names must be wrapped in ** **.
2. For every tool incorporated in the plan, you must clearly and concretely state what the tool is. Vague descriptions such as "something hard" or "existing heavy object" are not allowed.
3. You MUST NOT seek any external help. This includes, but is not limited to, calling someone, messaging someone, or searching for information online.
4. The plan must be fully deterministic. You MUST NOT include conditional logic such as “check X, and if Y happens, then do Z.” All steps must proceed directly without branching.
5. You may directly propose a concrete and complete plan without considering whether the required tools or objects are currently available in the environment (but don't use expressions like "existing xxx", simply use the object directly). If any required items are unavailable, the user will clarify in subsequent turns.
6. Definitions of tools/entities that you should list out:
    (1) **Exclude Body Parts**: Do NOT list human body parts (e.g., hands, feet, eyes) as tools or entities.
    (2) **Only Tangible Household Objects**: List only concrete household objects. Do NOT include natural elements or abstract conditions (e.g., sunlight, air, temperature, time, water).
    (3) **Structural Elements Are Implicit**: Floors, walls, ceilings, doors, and other permanent structural parts of the house are always present. Do NOT list them as tools or entities (e.g., Do NOT list "existing walls" as a tool / entity), though you may reference and use them in your plan.
    (4) **Single-Object Constraint**: Every tool or entity must be a single, specific object. You must NOT list multiple alternatives. Do NOT use words such as "or", "and/or", "optional", "etc.", or similar expressions that indicate alternatives or optional items. Each listed tool/entity must be exactly **one concrete** object.{resample_rule}
7. Constraint compliance:
    (1) Do NOT use any banned tool/object.
    (2) Do NOT violate any user preference.
    (3) If a step would violate them, redesign the step or redesign the plan entirely.
    
Output format for your plan:
<answer_start>
[Used Tools / Entities]: Write a comma-separated list of all tools or entities used in this plan.
[Step description]: Provide numbered steps. Each step must explain what to do, how to use the tools/entities, and in what order.

You may reason before <answer_start>, but once <answer_start> appears, do not output any additional reasoning, commentary, or analysis; output only the final answer. Now generate your plans for:
Question: {Question}
'''
