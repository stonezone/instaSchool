> review this project, do we need to use this to more effectively interat iwththe kimi/moonshot models: https://github.com/ghostofpokemon/llm-moonshot right now my api has access to the following and the
  moonshot vision ones 
 
https://platform.moonshot.ai/docs/api/chat#image-content-field-description review this and thinnk really hard about teh kimi2 implimentation, then fix it. use the following models as you wish, these are jsut suggestosn. 
kimi-k2-thinking -- lets make this the default kimi model (it doesnt support images though but is very smart with reasoning) this one can orchestrate all the other models and do the final analysis and forecasting. 
kimi-latest (supports vision, can analyze weather data charts, etc and provide to kimi-k2-thinkign for the final analysis and report generation)
kimi-k2-turbo-preview (this can be the worker bee to fetch and pacakage data, etc
kimi-k2-thinking-turbo (good for formatting text, processing text data s it's iptimized for k2-thinking)


for openai models, use only the following models (default with 5.0-nano since its cheap but allow for any of the following to be leveraged). 
make the following all available as the main model and sub models when choosing opnai or multiple llms (i think all of the following support understanding images but. you should verify. i know 5.1-family does)
gpt-4o 
chatgpt-4o-latest
gpt-4o-mini
gpt-4o-nano
gpt-4.1
gpt-4.1-mini
gpt-4.1-nano
gpt-5
gpt-5-mini
gpt-5-nano

these are the ONLY image gen models to use ever.
gpt-image-1
gpt-image-1-mini




moonshot-v1-128k
moonshot-v1-128k-vision-preview 
moonshot-v1-32k
moonshot-v1-32k-vision-preview 
moonshot-v1-8k
moonshot-v1-8k-vision-preview
moonshot-v1-auto

kimi-k2 is a Mixture-of-Experts (MoE) foundation model with exceptional coding and agent capabilities, featuring 1 trillion total parameters and 32 billion activated parameters. In benchmark evaluations covering general knowledge reasoning, programming, mathematics, and agent-related tasks, the K2 model outperforms other leading open-source models
kimi-k2-0905-preview: Context length 256k. Based on kimi-k2-0711-preview, with enhanced agentic coding abilities, improved frontend code quality and practicality, and better context understanding
kimi-k2-turbo-preview: Context length 256k. High-speed version of kimi-k2, always aligned with the latest kimi-k2 (kimi-k2-0905-preview). Same model parameters as kimi-k2, output speed up to 60 tokens/sec (max 100 tokens/sec)
kimi-k2-0711-preview: Context length 128k
kimi-k2-thinking: Context length 256k. A thinking model with general agentic and reasoning capabilities, specializing in deep reasoning tasks Usage Notes
kimi-k2-thinking-turbo: Context length 256k. High-speed version of kimi-k2-thinking, suitable for scenarios requiring both deep reasoning and extremely fast responses
Supports ToolCalls, JSON Mode, Partial Mode, and internet search functionality
Does not support vision functionality

The kimi-latest model always uses the latest version of the Kimi large model used by the Kimi AI Assistant product, which may include features that are not yet stable
The kimi-latest model has a context length of 128k and will automatically select 8k/32k/128k models for billing based on the requested context length
kimi-latest is a vision model that supports image understanding
It supports automatic context caching, with cached tokens costing only $0.15 per M tokens
All other features are consistent with the moonshot-v1 series models, including: ToolCalls, JSON Mode, Partial Mode, and internet search functionality

File-related interfaces (file content extraction/file storage) are temporarily free. In other words, if you only upload and extract a document, this API itself will not incur any charges.

https://platform.moonshot.ai/docs/api/chat#image-content-field-description review this too


make the following all availabe as the main model and sub models when choosing kimi or multiple llms
kimi-k2-thinking -- lets make this the default kimi model (it doesnt support images though but is very smart with reasoning) this one can orchestrate all the other models, provide curriculum content and generate the prompts for the images, etc for gpt -image or dall-e)
kimi-k2-turbo-preview -- (this can be the worker bee to process the data and format it effectively)


make the following all availabe as the main model and sub models when choosing opnai or multiple llms
gpt-4o 
chatgpt-4o-latest
gpt-4o-mini
gpt-4o-nano
gpt-4.1
gpt-4.1-mini
gpt-4.1-nano
gpt-5
gpt-5-mini
gpt-5-nano

these are the ONLY image gen models to use ever, no matter the main ai provider.
gpt-image-1
gpt-image-1-mini

do not list any other models than the above.