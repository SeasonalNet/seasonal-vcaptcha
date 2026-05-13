import sys, json, os, wave, subprocess
from vosk import Model, KaldiRecognizer

MODEL_PATH = os.environ.get("VOSK_MODEL", os.path.join(os.path.dirname(__file__), "model-small-en-us"))
GRAMMAR = '["zero","oh","one","two","three","four","five","six","seven","eight","nine","0","1","2","3","4","5","6","7","8","9"]'

def words_to_digits(text):
    m = {"oh":"0","zero":"0","one":"1","two":"2","three":"3","four":"4","five":"5","six":"6","seven":"7","eight":"8","nine":"9"}
    out=[]
    for w in text.strip().split():
        out.append(m.get(w, w))
    return "".join(ch for ch in "".join(out) if ch.isdigit())

def ensure_wav_mono16(path):
    try:
      wf = wave.open(path, "rb")
      ok = (wf.getnchannels()==1 and wf.getsampwidth()==2 and wf.getframerate() in (8000,16000))
      wf.close()
      if ok: return path
    except: pass
    tmp = path + ".mono16.wav"
    subprocess.call(["sox", path, "-r", "16000", "-c", "1", "-b", "16", tmp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return tmp

def transcribe(wav_path):
    wav_path = ensure_wav_mono16(wav_path)
    wf = wave.open(wav_path, "rb")
    model = Model(MODEL_PATH)
    rec = KaldiRecognizer(model, wf.getframerate(), GRAMMAR)
    rec.SetWords(False)
    txt=[]
    while True:
        data = wf.readframes(4000)
        if len(data)==0: break
        if rec.AcceptWaveform(data):
            j = json.loads(rec.Result())
            txt.append(j.get("text",""))
    j = json.loads(rec.FinalResult())
    txt.append(j.get("text",""))
    print(words_to_digits(" ".join(txt)).strip())
    return 0

if __name__ == "__main__":
    if len(sys.argv)<2:
        print("")
        sys.exit(2)
    sys.exit(transcribe(sys.argv[1]))
