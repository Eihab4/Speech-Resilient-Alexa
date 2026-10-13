// Runs on the browser's audio thread. Turns the microphone (usually 44.1 or 48 kHz float samples)
// into the 16-bit mono PCM Amazon Transcribe expects, and posts it in 100 ms chunks.
// The rate conversion is done here rather than by the AudioContext, so it works in every browser.

class Pcm16Processor extends AudioWorkletProcessor {
  constructor({ processorOptions }) {
    super();
    this.step = sampleRate / processorOptions.targetRate;
    this.chunkSize = processorOptions.targetRate / 10;
    this.chunk = new Int16Array(this.chunkSize);
    this.filled = 0;
    this.position = 0;
  }

  process(inputs) {
    const input = inputs[0]?.[0];
    if (!input) return true;

    for (; this.position < input.length; this.position += this.step) {
      // Average the input samples that make up one output sample, which also removes most aliasing.
      const from = Math.floor(this.position);
      const to = Math.min(input.length, Math.max(from + 1, Math.floor(this.position + this.step)));
      let sum = 0;
      for (let i = from; i < to; i += 1) sum += input[i];
      const sample = Math.max(-1, Math.min(1, sum / (to - from)));

      this.chunk[this.filled] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      this.filled += 1;
      if (this.filled === this.chunkSize) {
        // Transferring the buffer empties this.chunk, so the size is kept separately.
        this.port.postMessage(this.chunk.buffer, [this.chunk.buffer]);
        this.chunk = new Int16Array(this.chunkSize);
        this.filled = 0;
      }
    }
    this.position -= input.length;
    return true;
  }
}

registerProcessor("pcm-16", Pcm16Processor);
