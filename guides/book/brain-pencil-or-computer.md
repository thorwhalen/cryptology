---
title: "Brain, pencil or computer?"
subtitle: "Which parts of codebreaking to do by hand, which to hand over, and what each choice costs"
---

# Brain, pencil or computer?

**By the end you know which parts of codebreaking are worth doing by hand once, which are worth handing to a machine every time, and why that choice is less simple than either side likes to say.**

## Long division

Suppose you need to know what 7,834 divided by 46 is. You could do it with a pencil: it takes a few minutes and some care, and you might slip a digit. Or you could use a calculator, which takes three seconds and does not slip.

Nobody needs the answer to a division for its own sake. You want it because it tells you something: how many buses the school trip needs, or whether a cipher's length divides by 5. Doing it by hand slows down that purpose, and every other purpose you had that afternoon. So I use the calculator, and I think you should too.

That is the idea behind this book. Use the tools you have to the fullest, because every chore a tool takes off you frees your mind for the part that needs a mind.

## Every old way was once a new technology

People have argued about this for a long time. In Plato's dialogue *Phaedrus*, written about 2,400 years ago, Socrates worries that writing will make people forgetful: they will trust marks on a page instead of their own memory [1]. He was not wrong. Most of us remember far less by heart than people who could not read. But writing gave us libraries, science, and this book.

About 1,900 years later, the abbot Johannes Trithemius wrote *In Praise of Scribes*, arguing that monks should keep copying books by hand rather than trust the new printing press. He had it printed [2].

Writing, printing, even language itself: each was once the new technology, and each one cost us something and gave us more. Whatever you think of as "the old way" was someone else's new way.

## Codebreakers have always used machines

Codebreaking is where this argument was settled first. During the Second World War, the codebreakers at Bletchley Park in England did not break Enigma with pencils alone. Alan Turing, whose ideas still define what a computer is [3], designed the Bombe, a machine that checked possible Enigma settings far faster than any room of people could [4]. To break a different German cipher, the engineer Tommy Flowers built Colossus, one of the first electronic computers in the world [5]. Some of the first computers were built for exactly this job: breaking codes.

In any real situation today, a codebreaker gives the work to a computer. The programs exist, and with AI they need less and less help from a person. If all you want is the answer, how you get it does not matter: hand the ciphertext to a good solver. Guide 8, *Scoring and hill climbing*, shows how such programs work.

## So why learn any of it?

Because some of us want to know how it works, and you cannot judge a tool you do not understand. Doing something the slow way, once, brings the idea close. You feel why E stands out in a count of letters when you have made the tally marks yourself.

But the slow way has a cost too. Every hour spent counting letters is an hour not spent seeing the whole picture: which ciphers exist, how they relate, which attack fits which. The slow way brings one idea close and pushes the bird's-eye view further into the future.

So here is the rule this book follows: **do each mechanical task by hand once, so you know what the machine is doing for you. After that, let the machine do it.** Count the letters of one ciphertext with a pencil. Then never again.

## What a tool costs

A tool is not free. We pay for it with our own skills. Someone who always uses a calculator gets slower at mental arithmetic. That is called **deskilling**, and it is real.

But deskilling in one thing usually comes with **upskilling** in another. Freed from the chore, you spend your attention, your time and your creativity on something else, and you learn the skills that the new thing needs. A codebreaker who no longer counts letters by hand has time to learn statistics, or programming, or how a whole family of ciphers fits together.

So be aware of what a tool takes from you. But be at least as aware of what it costs to refuse it: all the time spent doing by hand what a machine could do, and everything you could have learned in that time instead.

## How this book helps you choose

Each guide teaches its method the classical way, with explanations, worked examples and exercises. It also has a section called **By hand or by computer**: a table of the jobs the method involves, roughly how long each takes by hand, and the tool that does it for you. Tools come in three kinds:

- **Tools to learn with**: the cryptology app's tools and exercises, and a set of spreadsheets that do the arithmetic while you watch every step. They show their working, so you can see what the method does.
- **Tools that just do it**: solvers that take a ciphertext and return the answer. Use them when the answer is all you need.
- **Your own programs**: the best tool of all is one you wrote yourself, because then you understand it completely.

The green boxes in the guides point into the app, and the footnotes point to the other tools. Even the learning tools are a stepping stone. They are for people who want, or need, to know how things work.

## For the adults

With AI, intelligence is becoming something anyone can switch on, like electricity. We are entering that age very fast; in my opinion, too fast, because it is not clear what we should be teaching our children. How to make the best use of machine intelligence? How to manage swarms of AI agents? More manual skills, leaving the thinking to machines, when robots may take over manual work too? It is hard to tell.

This book was composed around an app I made to get some kids I was teaching from meeting the ideas to playing with them, quickly. Should they count letters by hand? Once, yes, so that they appreciate what the computer does for them. And so on for every part of cryptanalysis.

I am betting that counting how many times each letter appears in a ciphertext is a waste of a child's time if they do it more than once. That is the philosophy of this book. A cryptanalysis curriculum, I believe, should be built around the best tools available, not around pencil and paper, with the pencil kept for the moments when it teaches something a tool cannot.

## Words to know

- **Deskilling**: losing a skill because a tool now does that job for you.
- **Upskilling**: learning a new skill, often in the time a tool has freed.
- **Solver**: a program that takes a ciphertext and returns the answer.
- **Bombe**: the machine Alan Turing designed at Bletchley Park to find Enigma settings.
- **Colossus**: one of the first electronic computers, built by Tommy Flowers at Bletchley Park to break the Lorenz cipher.

## References

1. Plato. [Phaedrus](https://www.gutenberg.org/ebooks/1636), 274c-275b. Translated by Benjamin Jowett. Project Gutenberg.
2. Trithemius J. In Praise of Scribes (De laude scriptorum), 1492; see [Johannes Trithemius](https://en.wikipedia.org/wiki/Johannes_Trithemius), Wikipedia.
3. Turing AM. [On computable numbers, with an application to the Entscheidungsproblem](https://doi.org/10.1112/plms/s2-42.1.230). Proceedings of the London Mathematical Society. 1937;s2-42(1):230-265.
4. [Bombe](https://en.wikipedia.org/wiki/Bombe), Wikipedia.
5. [Colossus computer](https://en.wikipedia.org/wiki/Colossus_computer), Wikipedia.
