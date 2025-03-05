from transformers import AutoProcessor, MusicgenForConditionalGeneration
import scipy

processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")

inputs = processor(
    text=["Happy electronic jingle for a food commercial"],
    padding=True,
    return_tensors="pt",
)

audio_values = model.generate(**inputs, max_new_tokens=500)

# Convert to audio file using scipy

scipy.io.wavfile.write("jingle.wav", rate=32000, data=audio_values[0, 0].numpy())
