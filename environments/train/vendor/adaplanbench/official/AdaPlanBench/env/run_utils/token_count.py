from transformers import AutoTokenizer

model_name = input("Model name: ")
text = input("Input text: ")

print("\nLoading tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(model_name)

tokens = tokenizer(text).input_ids

print("\nToken count:", len(tokens))
print("Tokens:", tokens)