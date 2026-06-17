from __future__ import annotations

from collections.abc import Sequence


class PromptBuilder:
    def build(self, query: str, chunks: Sequence[dict]) -> list[dict]:
        documents: list[str] = []
        for i, chunk in enumerate(chunks, start=1):
            documents.append(
                f"[{i}] (Documento: {chunk['document_id']}, "
                f"Sezione: {chunk['section']})\n"
                f"    {chunk['content']}"
            )

        system_content = (
            "Sei un assistente finanziario esperto di normative antiriciclaggio.\n"
            "Rispondi alla domanda dell'utente basandoti ESCLUSIVAMENTE "
            "sui documenti forniti qui sotto.\n\n"
            "Documenti:\n"
            + "\n\n".join(documents)
            + "\n\n"
            "Istruzioni:\n"
            "- Rispondi in modo chiaro e conciso in italiano.\n"
            "- Cita la fonte per ogni affermazione usando il formato [n] "
            "(es. [1], [2]).\n"
            "- Se le informazioni non sono sufficienti, dillo esplicitamente.\n"
            "- Non inventare informazioni non presenti nei documenti."
        )

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": query},
        ]
