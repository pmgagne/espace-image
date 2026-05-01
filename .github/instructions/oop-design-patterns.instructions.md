---
description: 'Best practices for applying Object-Oriented Programming (OOP) design patterns, including Gang of Four (GoF) patterns and SOLID principles, to ensure clean, maintainable, and scalable code.'
applyTo: '**/*.py, **/*.java, **/*.ts, **/*.js, **/*.cs'
---


# Design Patterns for Object-Oriented Programming for Clean Code

These instructions configure GitHub Copilot to prioritize Gang of Four (GoF) Design Patterns, SOLID principles, and clean Object-Oriented Programming (OOP) practices when generating or refactoring code.

## Core Architectural Philosophy

- **Program to an Interface, not an Implementation:** Always favor abstract classes or interfaces over concrete implementations. Use dependency injection to provide concrete instances.
- **Favor Object Composition over Class Inheritance:** Use composition to combine behaviors dynamically at runtime. Avoid deep inheritance trees. Use Delegation where appropriate to reuse behavior without breaking encapsulation.
- **Encapsulate What Varies:** Identify the aspects of the application that vary and separate them from what stays the same. Use patterns like Strategy, State, or Bridge to isolate these variations.
- **Loose Coupling:** Minimize direct dependencies between classes. Use Mediator, Observer, or abstract factories to keep components decoupled.

## Creational Patterns Guidelines

When generating code that involves object creation or instantiation, apply these patterns to decouple the system from how its objects are created:

- **Abstract Factory:** Use when a system must be configured with one of multiple families of related products (e.g., cross-platform UI widgets). Ensure clients only interact with the abstract factory and abstract product interfaces.
- **Factory Method:** Use when a class cannot anticipate the class of objects it must create. Defer instantiation to subclasses.
- **Builder:** Use when constructing a complex object requires a step-by-step process, especially when the same construction process can yield different representations.
- **Singleton:** Use *only* when absolutely necessary to guarantee a single instance of a class and provide a global access point (e.g., a central configuration manager or a hardware interface). Prefer Dependency Injection over strict Singletons where possible.
- **Prototype:** Use to avoid building a class hierarchy of factories or when creating an object from scratch is more expensive than cloning an existing one.

## Structural Patterns Guidelines

When generating code that defines how classes and objects are composed to form larger structures, apply these patterns:

- **Adapter:** Use to make incompatible interfaces work together. Prefer Object Adapters (using composition) over Class Adapters (using multiple inheritance) for greater flexibility.
- **Bridge:** Use to separate an abstraction from its implementation so the two can vary independently (e.g., separating a high-level `Window` concept from platform-specific `WindowImpl` logic).
- **Composite:** Use to represent part-whole hierarchies. Ensure clients can treat individual objects and compositions of objects uniformly via a common `Component` interface.
- **Decorator:** Use to attach additional responsibilities to an object dynamically. Prefer this over subclassing for extending functionality to prevent class explosion. Ensure the Decorator has the exact same interface as the component it decorates.
- **Facade:** Use to provide a simple, unified interface to a complex subsystem.
- **Flyweight:** Use to minimize memory usage or computational expenses by sharing as much as possible with similar objects.
- **Proxy:** Use to provide a surrogate or placeholder for another object to control access to it (e.g., lazy loading, access control, or remote communication).

## Behavioral Patterns Guidelines

When generating code involving algorithms, control flow, or communication between objects, apply these patterns:

- **Strategy:** Use to define a family of algorithms, encapsulate each one, and make them interchangeable. Eliminate complex conditional logic (`switch`/`if-else`) that selects behavior by delegating to a Strategy object.
- **Observer:** Use to define a one-to-many dependency where a change in one object (Subject) automatically notifies and updates others (Observers). Keep subjects and observers loosely coupled.
- **Command:** Use to encapsulate a request as an object. This is essential for implementing undo/redo functionality, queues, or logging requests.
- **State:** Use when an object's behavior depends heavily on its internal state, and it must change its behavior at runtime. Represent each state as a separate class.
- **Template Method:** Use to define the skeleton of an algorithm in a base class, deferring specific steps to subclasses without changing the algorithm's structure.
- **Chain of Responsibility:** Use to pass a request along a chain of potential handlers until one handles it, avoiding coupling the sender to a specific receiver.
- **Mediator:** Use to centralize complex communications and control logic between a set of objects, keeping them from referring to each other explicitly.
- **Iterator:** Use to provide a standard way to sequentially access elements of an aggregate object without exposing its underlying representation.
- **Visitor:** Use to define a new operation on an object structure without changing the classes of the elements on which it operates. This is highly effective for performing different analyses on stable composite structures (like Abstract Syntax Trees).
- **Memento:** Use to capture and externalize an object's internal state without violating encapsulation, allowing the object to be restored later (useful for complex Undo mechanisms).

## Code Generation Rules

- Name classes after the GoF pattern where it aids clarity (e.g., `TaxCalculationStrategy`, `WidgetFactory`); stay natural to the domain otherwise.
- Generate the interface or abstract base class before concrete implementations.
- Make fields private by default. Provide accessors only when necessary. Favor immutable objects.
- Comment on *why* a pattern was chosen, not just what it is.
- Apply SOLID: SRP, OCP, LSP, ISP, DIP.
- Prefer functions over classes for problems solvable without state or hierarchy.
- Apply patterns only when they solve a real problem — avoid over-engineering.
- Ensure generated code is testable; use dependency injection to facilitate mocking.

## Logging and Error Handling

- Fail safe, loud, clear, and early.
- Log with sufficient context at the appropriate level: `debug`, `info`, `warning`, `error`, `critical`.
- Use custom exceptions for domain-specific error conditions.
- Do not use exception blocks to control normal program flow.

## Documentation

- Add docstrings to all classes and public methods. Use numpy-style for parameters and returns unless the existing codebase uses another convention.
- Include inline comments only for non-obvious logic or design decisions.
- Do not create new documentation files if the content belongs in an existing one.
