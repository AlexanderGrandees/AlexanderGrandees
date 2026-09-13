# Vexi Speech Canonicalizer

Vexi v0.1.3 adds a conservative normalization layer between STT and the action router.

```text
Whisper output
-> normalization
-> known capability/entity vocabulary
-> semantic-family + command-context gate
-> confidence + margin check
-> canonical text
-> Intent Router
```

## Safety invariant

String similarity alone is never enough to execute an unrelated action.

Examples:

- `включи CDR на компе` can resolve `CDR -> HDR` because the words `включи` and `на компе` strongly support the display/HDR family.
- standalone `CDR` does not automatically trigger HDR.
- `открой CDR файл` remains file-oriented and is not rewritten to HDR.
- `HDR, а не CDR` is treated as an explicit user correction and can store a local confirmed mapping scoped to the display family.

## Learned corrections

Confirmed corrections are stored locally and are still gated by semantic family/context. A learned alias does not become an unrestricted global string replacement.

The canonicalizer is intended for terms such as HDR, browser/app names, service names, device names and user-specific technical vocabulary. It is not a general autocorrect engine for arbitrary speech.

## Regression requirements

- known STT variants are recognized in supporting context;
- cross-family similar words do not invoke the wrong tool;
- explicit corrections persist locally;
- learned corrections remain context-scoped;
- canonicalization events are logged as metadata without secrets;
- ambiguous input remains non-executing until resolved.
