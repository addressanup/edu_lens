# EduLens — Product Overview

**An AI learning companion for everyone.**

## Purpose

EduLens helps people make sense of what they are learning by combining visual context, conversation, and spoken guidance. Its role is to support understanding: help someone identify the next step, explore a concept, and build confidence through practice.

## Who it is for

EduLens is intended for anyone seeking learning support, including people studying independently, developing professional skills, revisiting a subject, or exploring a new interest. The product should not assume a specific age, grade, household role, or formal education setting.

Explanations should adapt to the learner's stated goals, prior knowledge, accessibility needs, preferred language, and pace. These are design goals, not a claim that every subject or adaptation is already implemented.

## The problem

Learning support often loses the context of the task in front of a person. Typing out a problem can interrupt concentration, generic answers can miss the source of confusion, and scheduled tutoring may not be available at the moment help is needed.

EduLens aims to make assistance available within the flow of learning: see the material, understand the question, and offer a useful next step.

## Core experience

1. **Start a session:** choose what to work on and share relevant context.
2. **Show or describe the task:** point a camera at learning material or ask a question in text.
3. **Receive guidance:** get a clear explanation, a guiding question, or a small next step.
4. **Continue at your own pace:** ask follow-up questions and adjust the level of explanation.

Audio-first responses can help people keep their attention on the material. Visual input should be optional wherever the task does not require it, and the interface should make capture and session state clear.

## Product principles

- **Inclusive by default:** address the user directly and use terms such as learner, person, and learning session.
- **Understanding over answer copying:** use questions and explanations to help the learner reason through a task.
- **Adapt to demonstrated knowledge:** avoid equating age with ability or assuming a particular curriculum.
- **Be honest about uncertainty:** ask for clearer context and acknowledge when an answer cannot be established.
- **Keep the user in control:** make camera use, audio playback, and session ending easy to understand and control.
- **Protect privacy:** minimize collected information and clearly explain when content is sent to an external service.
- **Maintain safe, respectful guidance:** preserve safeguards while making the learning experience relevant to a broad audience.

## Current implementation

The repository contains a FastAPI backend, an Expo camera-tutoring client, a browser demo, and modules for vision, audio, tutoring, observation, and personalization. The live tutoring path accepts camera frames and questions over WebSocket and returns guidance that the mobile client can read aloud.

The current camera device is a phone. Smart glasses remain a possible future interface, not a verified hardware product. AI capabilities depend on the configured provider and model.

EduLens is at an alpha stage. Existing screens, prompts, profile models, and some curriculum components still carry assumptions from an earlier product scope. Updating those components for the general-audience direction requires implementation and verification beyond this overview.

## Intended use cases

- Working through unfamiliar learning material during independent study.
- Revisiting foundational concepts before moving to a more advanced topic.
- Asking follow-up questions about a page, diagram, or practice problem.
- Building new skills through guided practice and explanations.

These use cases describe the intended direction; coverage must be validated for each subject and level.

## Development priorities

1. Align onboarding, terminology, prompts, and profiles with a general audience.
2. Let users express learning goals and preferred explanation depth without restrictive assumptions.
3. Validate tutoring quality across varied subjects, experience levels, and learning contexts.
4. Improve accessibility and control over visual and spoken interaction.
5. Complete authentication and authorization before shared or public deployment.
6. Document actual data handling, persistence, and provider behavior clearly.

## Scope of this revision

This overview replaces the original audience-specific concept and records the current product direction. Together with the root README, it updates product positioning; it does not claim that runtime behavior, historical specifications, or stored data contracts have already been migrated.
