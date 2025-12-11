#!/bin/bash

echo "=========================================="
echo "EduLens Speech Recognition Verification"
echo "=========================================="
echo ""

echo "1. Checking implementation files..."
if [ -f "src/audio/speech_recognizer.py" ]; then
    lines=$(wc -l < src/audio/speech_recognizer.py)
    echo "   ✓ speech_recognizer.py ($lines lines)"
else
    echo "   ✗ speech_recognizer.py MISSING"
fi

if [ -f "src/audio/child_speech_adapter.py" ]; then
    lines=$(wc -l < src/audio/child_speech_adapter.py)
    echo "   ✓ child_speech_adapter.py ($lines lines)"
else
    echo "   ✗ child_speech_adapter.py MISSING"
fi

if [ -f "src/audio/educational_vocabulary.py" ]; then
    lines=$(wc -l < src/audio/educational_vocabulary.py)
    echo "   ✓ educational_vocabulary.py ($lines lines)"
else
    echo "   ✗ educational_vocabulary.py MISSING"
fi

echo ""
echo "2. Checking configuration files..."
if [ -f "configs/audio/speech_config.yaml" ]; then
    echo "   ✓ speech_config.yaml"
else
    echo "   ✗ speech_config.yaml MISSING"
fi

echo ""
echo "3. Checking test files..."
if [ -f "tests/audio/test_speech_recognition.py" ]; then
    lines=$(wc -l < tests/audio/test_speech_recognition.py)
    echo "   ✓ test_speech_recognition.py ($lines lines)"
else
    echo "   ✗ test_speech_recognition.py MISSING"
fi

echo ""
echo "4. Checking documentation..."
if [ -f "SPEECH_RECOGNITION_README.md" ]; then
    echo "   ✓ SPEECH_RECOGNITION_README.md"
else
    echo "   ✗ SPEECH_RECOGNITION_README.md MISSING"
fi

if [ -f "SPEECH_RECOGNITION_IMPLEMENTATION_SUMMARY.md" ]; then
    echo "   ✓ SPEECH_RECOGNITION_IMPLEMENTATION_SUMMARY.md"
else
    echo "   ✗ SPEECH_RECOGNITION_IMPLEMENTATION_SUMMARY.md MISSING"
fi

echo ""
echo "5. Checking examples..."
if [ -f "examples/speech_recognition_example.py" ]; then
    echo "   ✓ speech_recognition_example.py"
else
    echo "   ✗ speech_recognition_example.py MISSING"
fi

echo ""
echo "6. Checking module exports..."
if grep -q "SpeechRecognizer" "src/audio/__init__.py"; then
    echo "   ✓ SpeechRecognizer exported"
else
    echo "   ✗ SpeechRecognizer NOT exported"
fi

if grep -q "ChildSpeechAdapter" "src/audio/__init__.py"; then
    echo "   ✓ ChildSpeechAdapter exported"
else
    echo "   ✗ ChildSpeechAdapter NOT exported"
fi

if grep -q "EducationalVocabulary" "src/audio/__init__.py"; then
    echo "   ✓ EducationalVocabulary exported"
else
    echo "   ✗ EducationalVocabulary NOT exported"
fi

echo ""
echo "7. Implementation Statistics..."
total_lines=$(cat src/audio/speech_recognizer.py src/audio/child_speech_adapter.py src/audio/educational_vocabulary.py | wc -l)
echo "   Total implementation: $total_lines lines"

test_lines=$(wc -l < tests/audio/test_speech_recognition.py)
echo "   Test suite: $test_lines lines"

echo ""
echo "=========================================="
echo "Verification Complete!"
echo "=========================================="
