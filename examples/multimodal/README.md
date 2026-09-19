# Images, audio and video

Level 1: one request that carries a picture and words together. A photo of an appliance's rating
plate goes in first, then the question, then, if there is one, a voice note that has already
been transcribed. The reply is checked against the two fields the caller asked for, so a reading
either parses or does not.

The image here is a reference, not bytes. Nothing in this repository ships a photograph, and an
example that runs on a stub has nothing to look at anyway. A real caller reads the file and
passes base64 in `ImagePart.data`, which is the form both documented backends take.

Audio does not go in as audio. Neither backend documents an audio input block, so both raise a
clear `NotImplementedError` instead of guessing a wire format. Transcribe first, send the
transcript as text.

Run it:

```
python -m examples.multimodal --model stub:scripted
```

The model and serial read off the rating plate, in the two fields the caller asked for, cited to
the image rather than to a document.

Every step is `decided_by: "code"`: the code assembles the parts, asks once, and checks the
reply. The model fills in what the reply says, not what happens next.
