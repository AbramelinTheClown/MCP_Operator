# Load model directly
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained("canopylabs/orpheus-3b-0.1-ft")
model = AutoModelForCausalLM.from_pretrained("canopylabs/orpheus-3b-0.1-ft")