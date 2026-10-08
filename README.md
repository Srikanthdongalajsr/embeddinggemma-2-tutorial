# EmbeddingGemma 2 in Practice

A hands-on notebook ([embeddinggemma2_practical.ipynb](embeddinggemma2_practical.ipynb)) for Google's multimodal embedding model, `google/embeddinggemma-2`. It covers:

- Loading only the encoders you need: text only (270M) up to text + image + audio (740M)
- Using query and document prompts, and why they matter
- Building a search over a mixed library of photos, sound clips and notes: index once with the full model, then search with the lightweight text-only model
