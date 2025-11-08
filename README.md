# Securing Model Inference with F5 Distributed Cloud API Security

<!-- CONTRIBUTOR TODO: update title ^^

*replace the H1 title above with your quickstart title*

TITLE requirements:
	* MAX CHAR: 64 
	* Industry use case, ie: Protect patient data with LLM guardrails

TITLE will be extracted for publication.

-- > 



<!-- CONTRIBUTOR TODO: short description 

*ADD a SHORT DESCRIPTION of your use case between H1 title and next section*

SHORT DESCRIPTION requirements:
	* MAX CHAR: 160
	* Describe the INDUSTRY use case 

SHORT DESCRIPTION will be extracted for publication.

--> 


## Table of contents

<!-- Table of contents is optional, but recommended. 

REMEMBER: to remove this section if you don't use a TOC.

-->

## Detailed description

This QuickStart shows how to protect AI inference endpoints on Red Hat OpenShift AI using F5 Distributed Cloud (XC) Web App & API Protection (WAAP) + API Security. You’ll deploy a KServe/vLLM model service in OpenShift AI, front it with an F5 XC HTTP Load Balancer, and enforce API discovery, OpenAPI schema validation, rate limiting, bot defense, and sensitive-data controls—without changing your ML workflow. OpenShift AI’s single-model serving is KServe-based (recommended for LLMs), and KServe’s HuggingFace/vLLM runtime exposes OpenAI-compatible endpoints, which we’ll secure via F5 XC

Key Components

- Red Hat OpenShift AI – Unified MLOps platform for developing and inference models at scale.
- F5 Distributed Cloud API Security – Provides LLM-aware threat detection, schema validation, and sensitive data redaction.
- Integration Blueprint – Demonstrates secure model inference across hybrid environments


### See it in action 

<!-- 

*This section is optional but recommended*

Arcades are a great way to showcase your quickstart before installation.

-->

### Architecture diagrams
![RAG System Architecture](docs/images/rag-architecture_F5XC.png)

| Layer/Component | Technology | Purpose/Description |
|-----------------|------------|---------------------|
| **Orchestration** | OpenShift AI | Container orchestration and GPU acceleration |
| **Framework** | LLaMA Stack | Standardizes core building blocks and simplifies AI application development |
| **UI Layer** | Streamlit | User-friendly chatbot interface for chat-based interaction |
| **LLM** | Llama-3.2-3B-Instruct | Generates contextual responses based on retrieved documents |
| **Embedding** | all-MiniLM-L6-v2 | Converts text to vector embeddings |
| **Vector DB** | PostgreSQL + PGVector | Stores embeddings and enables semantic search |
| **Retrieval** | Vector Search | Retrieves relevant documents based on query similarity |
| **Storage** | S3 Bucket | Document source for enterprise content |



## Requirements


### Minimum hardware requirements 

<!-- CONTRIBUTOR TODO: add minimum hardware requirements

*Section is required.* 

Be as specific as possible. DON'T say "GPU". Be specific.

List minimum hardware requirements.

--> 

### Minimum software requirements

- OpenShift Client CLI - [oc](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/cli_tools/openshift-cli-oc#installing-openshift-cli)
- OpenShift Cluster 4.18+
- OpenShift AI
- Helm CLI - helm


### Required user permissions

- Regular user permission for default deployment
- Cluster admin required for *advanced* configurations


## Deploy

*The instructions below will deploy this quickstart to your OpenShift environment.*

*Please see the [local deployments](#local-deployment) section for additional deployment options.* 

### Prerequisites
- [huggingface-cli](https://huggingface.co/docs/huggingface_hub/guides/cli) (optional)
- [Hugging Face Token](https://huggingface.co/settings/tokens)
- Access to [Meta Llama](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct/) model
- Access to [Meta Llama Guard](https://huggingface.co/meta-llama/Llama-Guard-3-8B/) model
- Some of the example scripts use `jq` a JSON parsing utility which you can acquire via `brew install jq`

### Supported Models

| Function    | Model Name                             | Hardware    | AWS
|-------------|----------------------------------------|-------------|-------------
| Embedding   | `all-MiniLM-L6-v2`                     | CPU/GPU/HPU |
| Generation  | `meta-llama/Llama-3.2-3B-Instruct`     | L4/HPU      | g6.2xlarge
| Generation  | `meta-llama/Llama-3.1-8B-Instruct`     | L4/HPU      | g6.2xlarge
| Generation  | `meta-llama/Meta-Llama-3-70B-Instruct` | A100 x2/HPU | p4d.24xlarge
| Safety      | `meta-llama/Llama-Guard-3-8B`          | L4/HPU      | g6.2xlarge

Note: the 70B model is NOT required for initial testing of this example. The safety/shield model `Llama-Guard-3-8B` is also optional.

### Installation Steps

#### 1. Login to OpenShift

Log in to your OpenShift cluster using your token and API endpoint:

```bash
oc login --token=<your_sha256_token> --server=<cluster-api-endpoint>
```

> Example: The observed deployment logged into `https://api.gpu-ai.bd.f5.com:6443` using a specific token and used project `z-ji` initially.

---

#### 2. Clone the Repository

Clone the F5-API-Security repository:

```bash
git clone https://github.com/rh-ai-quickstart/F5-API-Security
```

> The repository was cloned into the local directory.

---

#### 3. Navigate to Deployment Directory

Change into the cloned repository and then into the `deploy` folder:

```bash
cd F5-API-Security
cd deploy
```

> The deployment process navigated to `~/F5-API-Security/deploy`.

---

#### 4. Configure and Deploy

Execute the deployment script:

```bash
./deploy.sh
```

If the configuration file is missing, the script creates one and prompts you to edit it:

```
Values file not found. Copying from example...
Created /Users/<user>/F5-API-Security/deploy/f5-ai-security-values.yaml
Please edit this file to configure your deployment (API keys, model selection, etc.)
```

After editing `f5-ai-security-values.yaml`, re-run the script:

```bash
./deploy.sh
```

During installation, the script:
- Updates Helm dependencies.
- Downloads required charts (`pgvector`, `llm-service`, `llama-stack`).
- Creates the OpenShift project `f5-ai-security`.
- Installs the Helm chart with custom values.

A successful deployment will show:

```
NAME: f5-ai-security
LAST DEPLOYED: Thu Nov 6 12:27:49 2025
NAMESPACE: f5-ai-security
STATUS: deployed
REVISION: 1
TEST SUITE: None
Deployment complete!
```

---

### Post-Deployment Verification (Optional)

Once deployed, you can verify that the model endpoints are running correctly using `curl`.

### #Check Deployed Models (LlamaStack Endpoint)

```bash
curl -sS http://llamastack-f5-ai-security.apps.gpu-ai.bd.f5.com/v1/models
```

> Expected output: Two models available — a large language model and an embedding model.

---

#### Test Chat Completion (LlamaStack Endpoint)

```bash
curl -sS http://llamastack-f5-ai-security.apps.gpu-ai.bd.f5.com/v1/openai/v1/chat/completions   -H "Content-Type: application/json"   -d '{
    "model": "remote-llm/RedHatAI/Llama-3.2-1B-Instruct-quantized.w8a8",
    "messages": [{"role": "user", "content": "Say hello in one sentence."}],
    "max_tokens": 64,
    "temperature": 0
  }' | jq
```

> Example output:  
> `"Hello, how can I assist you today?"`

---

#### Test Chat Completion (Secured vLLM Endpoint)

```bash
curl -sS http://vllm-quantized.volt.thebizdevops.net/v1/openai/v1/chat/completions   -H "Content-Type: application/json"   -d '{
    "model": "RedHatAI/Llama-3.2-1B-Instruct-quantized.w8a8",
    "messages": [{"role": "user", "content": "Say hello in one sentence."}],
    "max_tokens": 64,
    "temperature": 0
  }' | jq
```

> This test against the dedicated vLLM endpoint also returned a successful response.

---

#### Summary

The deployment successfully sets up the F5-API-Security QuickStart environment on OpenShift, installs the Helm chart, and exposes model endpoints that can be verified using standard API calls.

---
---

## Next Steps: Deploying and Securing (Steps 2 & 3)

With the core AI baseline deployed, proceed to the detailed guides for configuring the F5 Distributed Cloud components and running security use cases:

### Step 2: Deploy F5 Distributed Cloud
Configure the F5 Distributed Cloud components and integrate the LLM endpoint.  
➡️ [Deployment and Configuration of F5 Distributed Cloud](docs/f5_xc_deployment.md)

### Step 3: Configure and Run Use Cases for F5 Distributed Cloud
Run security testing to demonstrate how F5 API Security protects the deployed model inference services.  
➡️ [Security Use Cases and Testing](docs/securing_model_inference_use_cases.md)

---



### Delete

<!-- CONTRIBUTOR TODO: add uninstall instructions

*Section required. Include explicit steps to cleanup quickstart.*

Some users may need to reclaim space by removing this quickstart. Make it easy.

-->

## References 

<!-- 

*Section optional.* Remember to remove if do not use.

Include links to supporting information, documentation, or learning materials.

--> 

## Technical details

<!-- 

*Section is optional.* 

Here is your chance to share technical details. 

Welcome to add sections as needed. Keep additions as structured and consistent as possible.

-->

## Tags

<!-- CONTRIBUTOR TODO: add metadata and tags for publication

TAG requirements: 
	* Title: max char: 64, describes quickstart (match H1 heading) 
	* Description: max char: 160, match SHORT DESCRIPTION above
	* Industry: target industry, ie. Healthcare OR Financial Services
	* Product: list primary product, ie. OpenShift AI OR OpenShift OR RHEL 
	* Use case: use case descriptor, ie. security, automation, 
	* Contributor org: defaults to Red Hat unless partner or community
	
Additional MIST tags, populated by web team.

-->
