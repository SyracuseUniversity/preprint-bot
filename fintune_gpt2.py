from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer, DataCollatorForLanguageModeling
from datasets import load_dataset
import torch

# Load dataset
dataset = load_dataset("json", data_files="finetune_data.jsonl")

model_name = "gpt2"
tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token
model = AutoModelForCausalLM.from_pretrained(model_name)

# Tokenize
def tokenize(batch):
    full_text = batch["prompt"] + "\n\n### Summary:\n" + batch["response"]
    return tokenizer(full_text, truncation=True, padding="max_length", max_length=1024)

tokenized_data = dataset.map(tokenize, batched=False)
tokenized_data.set_format(type="torch", columns=["input_ids", "attention_mask"])

# Training setup
training_args = TrainingArguments(
    output_dir="./gpt2-finetuned-summary",
    per_device_train_batch_size=2,
    num_train_epochs=3,
    learning_rate=5e-5,
    logging_steps=10,
    save_steps=200,
    save_total_limit=2,
    fp16=torch.cuda.is_available(),
)

data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_data["train"],
    tokenizer=tokenizer,
    data_collator=data_collator,
)

trainer.train()
