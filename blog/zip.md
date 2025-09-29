# ZIP File Format Considered Harmful

The `.zip` file format has a few problems.

## Am I in danger?

No, you're probably fine.
Although the title is catchy, the issues with the ZIP file format almost never affect end users.
The problems mostly affect maintainers of software that works with ZIP files in an automated fashion.
If that's what you do, then _yes you may be in danger_.

This blog post is mostly for maintainers of software that read and write ZIP files at the binary level,
like I do here: https://github.com/thejoshwolfe/yauzl , https://github.com/thejoshwolfe/yazl .
And yes, _I am in danger_, which I discovered while doing the research that brought me to this blog post.

## The Problems

We've been using `.zip` files for 35 years.
You'd think there'd be a technical specification for the format by now.
And you'd be correct; the format has been openly documented in the public domain since it was invented.
You can read the specification, which I'll refer to as APPNOTE, here: https://support.pkware.com/pkzip/appnote (version 6.3.10).

But there are problems.
If you don't need convincing and you just want the solution, skip ahead to The Solution.

The specification is maintained by a single for-profit corporation, PKWARE Inc., who originally created the format.
The process for contributing is to send snail mail or email with questions or requests for changes (APPNOTE section 1.5.1),
which I did on 2025-February-1st suggesting a few example changes and asking if they would be interested in discussing it further.
(Full text of my email is here: https://wolfesoftware.com/email-to-pkware.html .)
6 months later, I haven't gotten any response.

PKWARE hasn't fully given up on updating the document; the most recent version was published in 2022.
However, the changes they're making aren't addressing the most pressing need, which is:

### The ZIP File Format is Ambiguous

If you give the same `.zip` file to different unzipping programs, you'll get different results.
For example: https://wolfesoftware.com/ambiguous.zip .

* In a Gmail attachment preview, the `.zip` contains a single file called `Report.pdf`.
* If you download the attachment and extract it using Windows right-click `Extract All...`, you instead get a file called `Hacker.pdf`.

Gmail and Windows have different implementations of the ZIP file format that interpret ambiguities differently.

And yes this is a security problem.
Check out Gynvael Coldwind's 2.5hr deep dive into how ZIP file ambiguities could be used to take full control over a fictional yet plausible file server: https://gynvael.coldwind.pl/?id=682 .
The above example of changing a file's name is one of many problems I will discuss below.

### How Did This Happen?

The single biggest design flaw has been in the ZIP file format since the very beginning, version 1.0, in 1989.
Phil Katz of PKWARE, Inc. and Gary Conway of Infinity Design Concepts, Inc. designed the format, and they both missed it.
If you're familiar with the ZIP file format, you probably already know what it is;
it's The EOCDR Signature Search Problem I explain later on.

But I want to empathize with the design and defend it a little before I tear it to shreds.
`.zip` files are unquestionably valuable to humanity.
The file format works; it really does; that's why it's everywhere.
It was an improvement over the now-defunct ARC format, and the heroic decision to publicly document the format is probably the biggest contributing factor to its success.
I'm going to complain a lot about the problems with ZIP files, but I only care this much, because the format is so useful and successful.

Back in 1989, I imagine people weren't as worried about hackers.
Computer programmers were delighted to make stuff work at all, and less excited about preventing it from working in unintended ways.
The ZIP file format has redundant features, optional variability, room for future extension,
and other evidence that the designers were thrilled to venture forth into the wondrous world of possibility.

Now that it's 2025, that wonder has petrified; the possibilities are mapped out.
Archive format innovation is mostly done, and many of us don't want all the rough edges of the experimental design phase
to trip us up when we just want to close our Jira tickets and clock out at the end of our sad workdays.

I have the utmost reverence for whatever motivates people to create a file format,
and then further motivates them to give it to the world for free
(and then charge money for their proprietary implementation; people gotta eat.).
Passionate innovation is literally sacred to me; I want to honor it when I see it,
and the ZIP format design wears its passion on its sleeve.

But in my interpretation of the history, it was exactly this starry eyed techno-optimism that allowed many of the biggest problems with the ZIP format to exist.
When all you're focusing on is getting the best case scenario to work, you fail to scrutinize the corner cases.
"Sure an obscure bug could theoretically happen, but what are the chances? It'll be fiiiine."
Well, the chances that a hacker triggers an obscure bug on purpose is approximately 100%.

I don't want to sour anyone's passionate optimism, but we need to face the reality that bad actors exist.

### ZIP File Structure

I'm going to lead you on a hike through the technical details of the ZIP file format and point out all the cute little problems we find along the path.
I'd rate this hike a difficulty "medium", appropriate for beginner or aspiring programmers, but probably not interesting to non-programmers.
If you're not wearing your technical-details hiking boots today, you can skip ahead to The Solution where we'll all sit around the fire and share some hot chocolate and lamentations.
Let's begin!

A ZIP file is both a _compression_ algorithm (called DEFLATE) and an _archive_ format.
A compression algorithm transforms arbitrary data to take up less space,
and an archive format packs multiple files together into a single file.
The compression part of the ZIP file format is in good shape; I don't have any complaints.
I'm here to complain about the _archive_ part.

Imagine you've downloaded an album of MP3 songs.
You have a `.zip` file that contains a dozen or so `.mp3` files.
Each of the `.mp3` files is called an _entry_ in the archive.
Inside your `.zip` file, you can find not just the contents of those `.mp3` files,
but also information on where each entry starts and ends, the file name of each entry, and a bit more metadata.

A ZIP file looks roughly like this:
```
for each entry {                            //
    struct LocalFileHeader {                // ┌─> ########################
        entry.fileName                      // │   # "01 - Overture.mp3"  #
        entry.fileSize                      // │   # 3MiB                 #
    }                                       // │   ########################
    compressed {                            // │
        entry.contents                      // │   🎼🎵🎵🎵🎵🎵🎵🎵🎵🎵🎵🎵🎵🎵
    }                                       // │
}                                           // │
for each entry {                            // │
    struct CentralDirectoryHeader {         // │   ######################## <─┐
        entry.fileName                      // │   # "01 - Overture.mp3"  #   │
        entry.fileSize                      // │   # 3MiB                 #   │
        entry.st_mode                       // │   # 0o100644             #   │
        pointer to LocalFileHeader          // └─────o                    #   │
    }                                       //     ########################   │
}                                           //                                │
struct EndOfCentralDirectoryRecord {        //     #####                      │
    pointer to first CentralDirectoryHeader //     # o────────────────────────┘
}                                           //     #####
```

Contrast this with the TAR file format, which looks roughly like this:

```
for each entry {
    struct Header {
        entry.fileName
        entry.fileSize
        entry.st_mode
    }
    entry.contents
}
// No central directory in a TAR archive.
```

In both formats, you encounter each entry's name and size before the entry's contents, which in TAR means you can read it from a stream.
The ZIP format was designed to be readable from a stream as well, and I'll get more into that later (in an ominously titled section Streaming Reading Doesn't Even Work).
But because the file names are interleaved with the file contents, and the file contents comprise the vast bulk of the total archive,
it's very slow to simply list the entry file names of a TAR archive; it requires jumping all over the place.
Listing names is important for GUIs (like the Gmail attachment preview), command line APIs (`unzip -l`),
and other situations where a human wants to be informed of what's going on before committing.

The big innovation in the ZIP format (over ARC and TAR) was the addition of the `CentralDirectoryHeader` structs at the end of the archive.
A concise index of just the metadata is perfect for performantly listing the entries.
It's a bit counter intuitive that it's at the end instead of the beginning, but that's more convenient for writing the archive for reasons I won't get into.

However, because the `CentralDirectoryHeader` structs are at the end, it takes a few non-trivial steps to find them when reading a `.zip` file.
We need to start by reading the very last thing in the archive, the `EndOfCentralDirectoryRecord`,
which contains a pointer to the first `CentralDirectoryHeader`.

OK, no big deal. Let's take a look at the structure of the `EndOfCentralDirectoryRecord` to find where that pointer is in the struct:

```
struct EndOfCentralDirectoryRecord = {
    // Name:              Type; //Offset,Size| Comment
    signature:            uint32le; //  0, 4 | Always 0x06054b50
    // [12 bytes of unimportant things]
    centralDirOffset32:   uint32le; // 16, 4 | <-------- We're looking for this.
    archiveCommentLength: uint16le; // 20, 2 |
    archiveComment:          bytes; // 22, archiveCommentLength
};
```

The `centralDirOffset32` field is at offset 16 out of 22 in the struct, and the struct is at the end of the file.
Does that mean we just need to read offset `end - 6`?

### The EOCDR Signature Search Problem

I'll repeat that the intent of the `EndOfCentralDirectoryRecord` is that you can read the ZIP file starting at the end.
That was always the point.

So why for the love of dogs is there a _variable-length_ `archiveComment` at the _end_ of the struct??!
That means that not only is the struct we're looking for starting at a variable offset from the end,
but the very last thing in the file is a comment that can contain _arbitrary bytes_.
What were Phil Katz and Gary Conway thinking!
This is an inexcusable design flaw.

I believe the intent is that the `signature` field with the value `0x06054b50` is supposed to mark the start of the struct.
So let's just go rummaging through the file looking for that value and hope we find the one the writer of the ZIP file intended.
Do we scan backwards from the end assuming as short a comment as possible?
Or do we scan forwards for the "first" signature we find?
Do we find as many as we can and use some heuristic to decide?

Because the `archiveComment` can contain arbitrary bytes, it's possible to fit a complete `EndOfCentralDirectoryRecord` inside the comment,
or even fit an entire ZIP file in the `archiveComment` as long as it's smaller than 65536 bytes.
Depending on your search strategy, you'll find completely different entries in the ZIP file, maybe `Report.pdf` or maybe `Hacker.pdf`.

APPNOTE gives no guidance on how a reader is supposed to find where the `EndOfCentralDirectoryRecord` starts,
however it contains this hilariously unclear statement: `A ZIP file MUST have only one "end of central directory record"` (APPNOTE 4.3.1, first introduced in version 6.3.3 in 2012).
How exactly is an `end of central directory record` defined, PKWARE?
How do I search for two of them to validate a ZIP file meets this "MUST" requirement?
Is the requirement that the value `0x06054b50` must only appear once? (It's not.)
Every expert I've consulted on this has come to the same interpretation of the spec:

APPNOTE defines the ZIP file format ambiguously.

Everyone's interpretation is correct! Everyone is wrong! Who's to say!
The leadership in this "authoritative" specification has failed us.

They've had 35 years to fix it (and possibly tried and failed to fix it with that hilariously unclear statement above??).
What we gonna do about it? I have an answer! I'll get to it later.
First I want to complain more, and you're going to listen (or skip ahead if you want).

There's another major category of ambiguity, and it's right there in the design.
It wasn't designed for ambiguity per se, but rather redundancy.

### `LocalFileHeader` vs `CentralDirectoryHeader`

Do you remember in the diagram that `entry.fileName` shows up twice?
The idea is that you can either read the `.zip` file from a stream or start by reading the central directory and you'll get the metadata you need either way.
That's a very nice idea, isn't it.

What if the file name in the `LocalFileHeader` is different from the one in the `CentralDirectoryHeader`?
https://wolfesoftware.com/local-vs-central.zip

Remember the spirit of the 1980s (as I imagine it); you don't think to guard against untrusted inputs;
you're thrilled by the wonder of possibility, drunk on power, excited to make the thing sparkle!
The spec says the file name is in both places, so you only need to read one of them!
Cool! Pick whichever one is more convenient! And now you're in danger!

This is the mindset I had when I wrote my implementation, so enthralled by making it do the thing that I didn't think about edge cases.
I was reading APPNOTE, and APPNOTE doesn't warn you to guard against edge cases (with a few exceptions I'll get to).
I wasn't in a mindset to distrust my fellow human, and nobody should be punished or blamed for believing in humanity!

When multiple unzip implementations work together, but they don't agree on how to interpret the ambiguities, that's a security hazard.
If your virus scanner or validation middleware is blocking `.exe` files or `.php` files by reading the central directory,
but then the application extracts the files by reading the local headers, then we have a "Houston, we have a problem.".

The safest behavior is for an implementation to check _both_ copies of the file name and if they disagree,
reject the whole zip file as malicious (your error message can say "corrupted" if you don't want to use scary language.).
In my research very few implementations actually do this. Mine doesn't. (I will fix it.)

If you are orchestrating zip implementations, rather than authoring them, then the safest thing is to use the same implementation everywhere.
That way there's no disagreement within your system over how to interpret the ambiguities.

The third major category of security problem is not specific to ZIP, but it's worth mentioning because of how poorly APPNOTE handles it.

### Path Traversal Vulnerabilities

Every archive format, including ZIP, encodes the file names of its entries. This is basic stuff.

Common examples of file names are `README.md`, `bin/build.sh`, `config/dev/app.env`, etc.
The ancestor directories (`bin/`, `config/`, and `config/dev/` in these examples) are implicitly required to be created when extracting the archive.

One way to create files during extraction is this:

1. `cd` into the output directory.
2. Create a file with the file name interpreted relative to the cwd.
3. Get hacked, because this is wrong.

In a rare moment of security consciousness, APPNOTE actually gives a warning about the danger in section 4.4.17.1.
`The path stored MUST NOT contain a drive or device letter, or a leading slash.`

If a ZIP file claims the `entry.fileName` is `/etc/passwd` or `C:/Windows/System32/nt.dll` (just a few examples),
then extracting to that path will install malware in your system.
Our algorithm above assumed the paths would always be relative, but we need to check for that.

Let's update to a more modern algorithm that avoids stateful `cd`, and also includes this check:

1. If the file name is absolute, error.
2. Create a file by joining the output path and the file name.
3. Get hacked, because this is still wrong.

APPNOTE was on to something saying the file name shouldn't be absolute (an inclusion since version 1.0!),
but then they apparently just gave up on that line of reasoning despite path traversal vulnerabilities being a well known exploit for decades.

What do you think happens if the `entry.fileName` is `../../../../etc/passwd`? Busted.
Just check for leading `../`? Get hacked by `dont/worry/../../../surprise.txt`.

The actual algorithm required to guard against path traversal is not trivial.
It's something like this:

1. Convert backslashes to forward slashes. (There's a good reason for this; it's complicated.)
2. Normalize the file name (e.g. convert `a/../b/.//c` to `b/c`). If this changes the file name, error; no excuses.
3. If the file starts with `[A-Za-Z]:` or `/` or `../`, error.
4. This is an approximation; don't try this at home.

So is this a problem with the ZIP file format?

Not really, actually.
It's a general problem with every archive format, and it's also very well known.
In my research, I didn't find any unzip implementation that would write files outside the extract directory.

Professional security researchers are watching out for this problem, and it usually gets caught before it causes too many incidents.
The process for finding and addressing these vulnerabilities is this:
first APPNOTE leads the way poorly, and then hundreds of security researchers finish the job by reporting bugs against hundreds of unzip implementations.
Can you imagine any possible improvement in this situation? I'll share my answer later.

Just how poorly is APPNOTE leading the way? Let's introduce a new complication you might have heard of.

Symlinks exist as a concept, which APPNOTE isn't really aware of.
(The only reference to "symbolic" is in section 4.5.7, which is a red herring.)

Symlinks are encoded by setting `entry.st_mode` (remember that from the diagram?) to something like `0o120777`.
APPNOTE is fully oblivious to anything about a "mode", but it's there.
In reality the `st_mode` is in the top 16 bits of `external file attributes` when the top 1 byte of `version made by` is `3`,
but APPNOTE isn't going to tell you that.

APPNOTE isn't the only one oblivious to symlinks.
In my research, only about 1 in 4 unzip implementations recognize when an entry is a symlink instead of a regular file.
In my own implementation, I was confidently oblivious, declaring it out of scope: https://github.com/thejoshwolfe/yauzl/issues/94 .

But guess what happens when you support symlinks!
You gotta validate the file name of the symlink _and_ validate the target that the symlink points to!

Consider a `.zip` file containing these two items:

* `dir` a symlink pointing to `/etc`
* `dir/passwd` you didn't just open this for writing, did you?

But are symlinks really part of the ZIP file format?
If only 1 in 4 implementations believe in symlinks, and our fearless leader APPNOTE doesn't, who's right?
I have an answer, that I'll get to later.

The next thing I want to point out is that `entry.st_mode` (remember the diagram?) is actually _not_ duplicated between the `LocalFileHeader` and `CentralDirectoryHeader`.
Did you catch that before I pointed it out?
Did Phil Katz and Gary Conway catch that before I pointed it out?

### Streaming Reading Doesn't Even Work

As much as I'd like to empathize with the original spirit of the design,
I have no idea why the `external file attributes` (aka `st_mode`) only appears in the `CentralDirectoryHeader` and not in the `LocalFileHeader`.
Regardless of whether we can figure out the motivation, the reality is that critical information is only available in the central directory.

This means if you're reading a ZIP file from a stream relying on the `LocalFileHeader` info,
you _cannot_ support symlinks; you literally don't have the necessary information,
and you're doomed to interpret symlinks as regular files.

And that's not even the worst of it.

Looking at the diagram I gave you might be misleading.
You might think that the first thing in a (non-empty) ZIP file is the first `LocalFileHeader`.
I will not apologize for misleading you, because APPNOTE includes essentially the same misleading diagram in section 4.3.6.

In reality, the first thing in a ZIP file could be anything, maybe a `LocalFileHeader`,
maybe a bunch of `\x00` bytes, maybe the header of an `.exe` Windows executable.
If you're reading from a stream, you're (sometimes) going to get a fire hose of "junk" data before you find the first `LocalFileHeader`.

This is a feature, not a bug! APPNOTE documents this "clearly" in section 4.1.9, which I will quote in full:
`ZIP files MAY be streamed, split into segments (on fixed or on removable media) or "self-extracting". Self-extracting ZIP files MUST include extraction code for a target platform within the ZIP file.`

Did you see it? Did you see where APPNOTE says there can be non-ZIP-related junk data before the first `LocalFileHeader`?
Alright, it's not clear at all.
If you don't know what a `"self-extracting"` ZIP file is, you have little hope of pickin' up what APPNOTE's puttin' down.

A self-extracting ZIP is a polyglot file; it is simultaneously a valid `.zip` file and a valid `.exe` file (usually with the `.exe` file extension);
an executable in front, and a ZIP in the back.
As long as you read the ZIP file starting at the end, the `EndOfCentralDirectoryRecord` and `CentralDirectoryHeader` pointers
will take you to all the content correctly and everything is fine.

As the name suggests, the executable code is some kind of program that will read and extract the ZIP entries from itself.

So what if you did try to read such a polyglot from a stream?
Imagine you're rummaging through executable code searching for what looks like a `LocalFileHeader`.
The first 4 bytes of a `LocalFileHeader` are `0x04034b50`.
So your program that reads zip files should probably go looking for that,
looking through the code of a program that reads zip files.

Uh oh.

Do you think that maybe the constant `0x04034b50` might show up the code of a program that reads ZIP files and not actually be the start of your `LocalFileHeader`?

"But it'll be fiiiine. Just don't read self-extracting ZIP files from a stream.
Just don't include the constant `0x04034b50` in your junk data.
Just tolerate incoherent-looking data and assume you should keep looking for the next `LocalFileHeader`.
Just stop worrying about edge cases and appreciate how fricking cool it is that we can have a polyglot `.zip` + `.exe` file!
How cool it is that you can read a ZIP from a stream!
How cool it is that you can add a comment to your `EndOfCentralDirectoryRecord`!
How cool!
What are the chances that things go wrong?"

APPNOTE gives no guidance on how to resolve this situation, but has the audacity to claim in the same sentence that you can stream a ZIP and that a ZIP can be self-extracting.
The leadership in this "authoritative" specification has failed us.

You may have noticed the use "MUST" and "MUST NOT" in all caps in the APPNOTE quotes.
I've got a lot of criticisms with the way APPNOTE uses or misuses these, but just to start here's an especially strange one from 4.3.1:
`Files MAY be added or replaced within a ZIP file, or deleted.`

(This is very out of place considering this from section 1.2:
`No specific use or application need is defined by this format and no specific implementation guidance is provided. This document provides details on the storage format for creating ZIP files.`)

OK, why is APPNOTE telling us that files MAY be deleted within a ZIP file?

A clever engineer might consider a very time-efficient way to delete an item from a ZIP file,
where you only need to remove the `CentralDirectoryHeader` and cause minimal shift disruption to the rest of the file.
Is that what APPNOTE means? Who knows!

Guess what's going to happen if you read a ZIP file from a stream that such a clever engineer has touched.
You'll encounter a zombie `LocalFileHeader` entry that was supposed to have been deleted.
But forget whether a clever engineer did something "efficient",
a hacker could intentionally create a ZIP archive with an orphaned `LocalFileHeader`.
Like this: https://wolfesoftware.com/orphan-lfh.zip

To all the unzip authors out there, please stop reading ZIP files from streams.
It looks like it should work, and then you get hacked.
It looks fine, and then you get a fire hose of junk.
It looks like it's well specified, and then you learn what a polyglot ZIP file is.

The stream is a lie. Only starting at the end will save you.

## The Solution

Welcome back if you skipped over the technical details hike.
My voice hurts from yelling.
Let's break out the hot chocolate.

### The Wrong Solution: Abandon Ship

You might be thinking: "if the ZIP file format sucks so much, we'd better make a new archive format.
Let's each make one that we like for ourselves and then maybe like 1 other person in the world will adopt one of them.
Here I'll go first: https://github.com/thejoshwolfe/poaf ."
(See also https://en.wikipedia.org/wiki/List_of_archive_formats and https://xkcd.com/927/ .)

No. I'll repeat what I said earlier in this blog post, because the fury I've expressed since then can give the wrong impression:

`.zip` files are unquestionably valuable to humanity. The file format works, and you are not in danger.

We don't need to abandon ZIP files. We need to fix them, and it's going to take surprisingly little effort.

Many newer archive formats have been invented since ZIP, and yet ZIP is still dominating nearly every archive use case.
ZIP is how we download music albums. ZIP is how we email files to our families.
ZIP has builtin support in Windows explorer.
ZIP is the basis of `.docx` and `.odt` files (Microsoft Office and LibreOffice documents).
ZIP is the basis of `.jar`, `.apk`, `.xpi`, `.ipa`, and countless others.

ZIP is everywhere, because it is fundamentally _good_.
It's a very good idea with a some very bad ideas stabbing out of it.

### The Right Solution: New Leadership

The problem is PKWARE.

I want to be very clear about something before I go on: I wish the very best for the human beings that are running PKWARE, Inc.
People need money, and for-profit businesses can have very positive effects.
I do not blame the humans who are currently working at PKWARE for the APPNOTE situation.
APPNOTE probably earns them very little profit, and they're wisely directing their efforts elsewhere.
(And if I'm wrong about this, I'm sorry! Also please respond to my email.)
Check out https://www.pkware.com/ if you're in the market for some enterprise data protection solutions.

The problem is that PKWARE, a for-profit company, isn't the leader the ZIP world needs.
We need a leader that accepts contributions and facilitates collaboration in an open platform.
In short, the ZIP file format specification needs to be open source.

And then we can begin the long, grueling process of addressing all the ambiguities and
providing guidance for implementers who believe in humanity,
and hey it would be nice if we had a standard test suite, wouldn't it?

So, I have spent the last several months writing a spec document addressing all the ambiguities and
providing guidance for implementers, and I've even created a standard test suite.

### Introducing Common ZIP

https://commonzip.org/

The Common ZIP project is a spec and a test suite.
It is strictly a volunteer operation; I do not want your money.

The Common ZIP Spec is a complete rewrite of the ZIP file format specification from scratch (excluding DEFLATE, CRC32, and UTF-8).
It is a guide to:

* creating ZIP files that can be read by most existing implementations,
* reading ZIP files created by most implementations,
* and guarding against surprising behavior from untrusted inputs.

Common ZIP is not a new archive format.
It's a descriptive and prescriptive specification of the ZIP file format we've been using all along.
APPNOTE doesn't understand symlinks; APPNOTE doesn't know which optional third-party extensions are actually used.
APPNOTE doesn't know that Windows Explorer sets the `version made by` to POSIX rather than NTFS.
Common ZIP does.

Here's a rundown of the solutions to all those problems we saw on our hike:
* Common ZIP resolves the EOCDR search ambiguity: you SHALL do the search backwards. (TODO: links)
* Common ZIP resolves the local-vs-central ambiguity: the two copies SHALL agree (on important things).
* Common ZIP includes an algorithm to prevent path traversal vulnerabilities.

And Common ZIP is an open-source project that accepts your input!
Find a mistake in spec? Post a publicly searchable bug report!
There are plenty of topics that would benefit from community collaboration.
If you're a ZIP expert, a ZIP enthusiast, or just ZIP interested, come join the discussion: https://github.com/common-zip/common-zip-spec/issues .

I estimate the specification is 90% written, and it's time to invite collaboration!
I've been researching existing ZIP implementations, studying APPNOTE,
and speaking with security experts enough to give an evidence-based recommendation on almost all topics.
The remaining TODO's are fairly uncontroversial and well-scoped tasks,
but feel free to open discussions for the topics that appear "done".
If there ever exists a "final" version of the Common ZIP spec, I'd want to allow at least a year of opportunity for people to contribute before nailing it down,
and I'm not sure it will ever be appropriate to "close" this open-source specification.

In addition to the specification document, I made a test suite of about a hundred `.zip` files
that get run through about a dozen unzip implementations such as Info-ZIP (command line `unzip`),
the standard libraries of Python, Go, and Java, and of course my own implementation in JavaScript.

The test suite distinguishes between:

* ✔️ strict compliance with the Common ZIP spec,
* `?` harmless non-compliance, and
* ⚠️ dangerous non-compliance.

I plan to open bug reports for the ⚠️ dangerous issues and hope for one of the following outcomes:
the implementation should change to no longer exhibit the dangerous behavior,
or the implementation should add a warning to its documentation,
or the maintainers of the implementation should join the Common ZIP discussion and advocate that it's not actually dangerous.

The test suite still has a lot of work to do.
I estimate the test case authoring is less than 50% done.
I've got a long list of TODO comments enumerating ideas for more tests.

We can always add more unzip implementations as test subjects.
If you've got an unzip implementation, I'd love to add it to the table!
You can open a PR or simply open an issue discussion: https://github.com/common-zip/common-zip-tests

Beyond the unzip tests, I haven't figured out how to make automated tests for implementations that _create_ zip files.
I'd love to hear from yall if you have ideas.
Fuzzing seems particularly interesting for testing zip creation.

Lots of people ask me about a "reference implementation", and I'm not sure it would be valuable.
But if we've got a test suite, it seems like a natural idea to make something that passes 100% of the cases, right?
Might be interesting.

### Why?

**Why should anyone trust your leadership?**
I hope to earn your trust through the quality and utility of my work.
I intend to base all normative claims on evidence in the real world, not idealistic philosophy.

I also don't intend to do this on my own.
The Common ZIP project is not under my personal GitHub account because I want it to be a project for the people by the people.
I have thus far put in the overwhelming bulk of the effort, and I intend to put in much more,
but this burden is inappropriate for a single enthusiast to bear alone.
If Common ZIP was exclusively mine, it would eventually starve for leadership once my enthusiasm dies.
To claim the Common ZIP project as my own would condemn it to the same fate that APPNOTE suffers today.

**Why did you bother doing all this work?**
This is a passion project born of a belief that the world deserves better than status quo.
I am in a position of financial privilege and technical experience such that I can afford the time and energy to do this all as a volunteer.
I refuse to accept monetary compensation for this labor, not even no-strings-attached donations,
because I am so sincere about the purity of my motivation.

I do however appreciate words of encouragement or even just seeing metrics go up indicating that people are aware of what I'm doing and appreciate it.
I'm doing this for the world, not for an abstract idea.
Enthusiasm is the funding for volunteer projects, and when I learn that the world is receiving the work I'm doing, I get "paid".
If you would like to express your appreciation, I suggest going here: https://github.com/common-zip/common-zip-spec/issues/1

**Why start from scratch instead of forking APPNOTE?**
Firstly, because I'm not allowed to fork APPNOTE.
Since APPNOTE version 6.3.3 published in 2012, section 1.4 strictly prohibits forking.
APPNOTE is "the exclusive property of PKWARE", which is a bit jarring
considering the press release on Valentines Day 1989 where Phil Katz and Gary Conway declared:
`The ZIP file format is given freely into the public domain and can be claimed neither legally nor morally by any individual, entity or company (or any other sentient creature in the universe.)`
( http://cd.textfiles.com/pcmedic9310/MAIN/MISC/COMPRESS/ZIP.PRS , https://web.archive.org/web/20040210234346/http://www.idcnet.us/ziphistory.html )

Secondly, APPNOTE in its current form is very well known, and I want it to stay recognizable as a reference.
This means sever limitations on how much overhaul and improvement can happen to it.
For example, the field in APPNOTE called `offset of start of central directory with respect to the starting disk number` is renamed in Common ZIP to `centralDirOffset32` (or perhaps it is given a name),
and I don't want code comments that reference the old name to become broken references.
With two competing specifications, it's possible to migrate your terminology from one spec to the other, if you're so inclined,
or simply stick with APPNOTE terminology and nobody should be confused.

## Imagining A Better Archive Format

Remember that abandoning ZIP is the wrong solution.
However, there's an alternate universe where PKWARE did things slightly differently, and we would be in a much better situation.
Let's have fun and turn our critical 20/20 hindsight to 1989. (You'll need your technical-details hiking boots for this section.)

1. `archiveComment` needs to come before `archiveCommentLength`, ideally before the signature too. This is the key to avoiding almost all ambiguity in the ZIP structure, although streaming readers would need to reach the end of the archive before understanding how accurate their interpretation has been to that point, it's still a dramatic improvement in clarity.
2. ZIP64 should have introduced different signatures for local and central headers and for the end record, and then just used the larger sizes in place of the smaller sizes. Trying to squeeze 64-bit support into the "optional" extension areas is a misfeature. An archive reader that doesn't support ZIP64 shouldn't even attempt to read the archive; it's going to get the sizes and offsets wrong. Don't try to make a half-compatible, wrongly-readable archive. Make archives appear corrupted if the reader can't read them.
3. Timestamp and CRC32 should have been optional in the extra fields. In lots of cases, you simply don't care about these, so the ability to omit them would be nice. Additionally, both timestamps and checksums are technologies that were experiencing innovation even in 1989, and ZIP should have been prepared to let them get updated with future bitwidths, formats, algorithms, etc.
4. Internal and external file attributes should have been extra fields instead of built into just the central header. APPNOTE doesn't even know what these fields do; they've been "host-system dependent" or reserved or whatever since the beginning. That's what extra fields should be used for. And then also we can have them in the local headers if we really want them (see symlinks).

None of these conflict with (my interpretation of) the design spirit.
Of course it would be nice if streaming reading worked and if all the security issues were thought out ahead of time,
but that kind of major change would limit what ZIP can be used for.
Just rearranging the layout of data is what we could have had, and it would have avoided a lot of problems.

We can take this thought experiment further and imagine what an archive format in 2025 actually needs.
If we were to design a format today, what would it look like?
I say it would look like this: https://github.com/thejoshwolfe/poaf .
Again I'll repeat that abandoning ZIP is not necessary; we can just fix a few bugs, and everything will be fine.
But if you want to start a new project in 2025 and you can afford to pick an obscure archive format to use,
get creative and design something specialized for your use case!
Innovation is a beautiful thing. Don't let the inertia of status quo shackle your imagination!

## Thanks

My 2025 has been filled with ZIP-related labor.
I'm very proud of what I've accomplished, and there's still a lot of work to do.
I'm thrilled that you care enough to read this blog post, and if you'd like to express enthusiasm for this particular blog post,
leave a ❤️ (and comment?) here: https://github.com/thejoshwolfe/wolfesoftware.com/pull/2 (requires a GitHub account).

To express enthusiasm for Common ZIP as a project, that's here: https://github.com/common-zip/common-zip-spec/issues/1 .
