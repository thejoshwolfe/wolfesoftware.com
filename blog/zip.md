# I fixed the ZIP file format

We've had 35 years to work out the kinks in the `.zip` file format, and now for the first time we've actually done it!

I've been working with the low-level ZIP file format for 10 years, and the technical specification has been in need of a major overhaul.
I tried reaching out to PKWARE, Inc., the for-profit maintainers of the official spec,
and they don't seem interested in doing any such overhaul.

So I rewrote the entire ZIP technical specification myself from scratch, and boy was this a doozy.
The new project is called Common ZIP, and you can find links in the References;
it includes the specification document and also a standardized test suite.
The bulk of the hard work is done at this point, and what we need now is for the maintainers of the dozens (possibly hundreds?) of ZIP implementations to fix a few bugs.

A ZIP utopia is right around the corner. Follow me and I'll take you there!

## What's the problem?

A file format is essentially a language that computer programs use to talk to each other.
One program makes a `.zip` file, and another program extracts it.
If they don't agree on what the 1's and 0's mean, it leads to miscommunication,
like the ZIP file containing a file with the wrong name, missing a file, or the ZIP being completely unreadable.
These misunderstandings might be accidental, but in rare circumstances hackers can exploit disagreements to bypass security measures.

Consider this example: https://wolfesoftware.com/ambiguous.zip

* In a Gmail attachment preview (as of writing this), the `.zip` contains a single file called `Report.pdf`.
* If you download the attachment and extract it using Windows right-click `Extract All...`, you instead get a file called `Hacker.pdf`.

I created this particular ZIP file intentionally to highlight the differences between implementations.
It's plausible that in certain technical contexts, this technique could be used to smuggle an `.exe` or `.php` file past a security scanner to install malware onto a computer system.
(Link to an in-depth study of this by Gynvael Coldwind in the References.)

ZIP is a very popular format, and security researchers have been finding and reporting problems with it for decades.
The most critical issues in ZIP handling software are either fixed or have known workarounds.
ZIP files aren't inherently dangerous, as long as we stay on top of the bugs, which humanity is mostly doing well.

The tragic thing about these bugs and miscommunications is that they could easily be avoided if the ZIP technical specification was improved.
The official spec, called APPNOTE (link in the References at the end), has three categories of problems:
it's missing critical information, it includes too much useless and distracting information,
and some of the useful information it does include is presented in a confusing way.

As an enthusiastic and ambitious software engineer in 2015, I decided to write my own implementation of the ZIP file format from scratch.
I read the official spec, and the guidance therein says to do A, B, and C, and optionally do hundreds of other things, say D-Q.
I did A, B, and C, and made a judgement call to pick out just D from the optional list.

Once I published and deployed my code, it started to attract attention,
and then dozens of users and security researchers found that I had fallen for the same problems as almost everyone else who's made ZIP software.
It's actually critical to do J, K, and L even though APPNOTE says that they're optional,
and also you must NOT do M (good thing I didn't), and also you need to do X, Y, and Z despite never being mentioned in APPNOTE.
The users and security researchers reported bugs one by one over the course of several years, and I fixed each one thanking them for their help.

And I'm not alone. I've personally heard from the developers of two more ZIP implementations that they had similar experiences,
and the public bug trackers and source code of dozens of other implementations tell the same story.
When stated this clearly, the solution seems obvious.
The technical specification needs to be updated; remove M; add X, Y, and Z; elevate J, K, and L to mandatory.
But we run into some snags.

Not everyone agrees on what SHOULD be the correct interpretation of the ZIP file format.
Even when presented with evidence based in security research, there's still pushback.
Why is that?

### Security vs Performance

There are some shady things you can do in a ZIP file that if detected should result in the whole thing being rejected as malicious.
For example, every file name is embedded within a ZIP file twice (or more), `Report.pdf`/`Report.pdf`,
and if the two copies conflict with each other, `Report.pdf`/`Hacker.pdf`, that's almost certainly an attack.
But in my research only about 1 in 4 implementations detect this conflict and report it as an error;
the rest simply pick one of the copies and believe it, and it's about 50/50 on which one they pick.

The best behavior for a ZIP implementation is to detect any conflicts and report an error, but that requires extra work.
The programmer has to do extra work to write the code, the code gets more complex and is extra work to maintain,
and the program has to do extra work at runtime to perform the check on every ZIP file.
It's not an onerous amount of effort, but it's certainly not the path of least resistance.

If a security researcher reports a bug against an implementation for neglecting this check, a reasonable reaction might be that it's not worth the effort.
So is checking for name conflict attacks really required? The security experts say it is, but the official spec does not.
Who do we believe?

If your answer is that security is important, and we should always guard against attacks, let me try to convince you otherwise.
The ambiguous ZIP file I linked above doesn't use this technique to cause conflicting names; it uses a more nefarious technique that is much harder to detect.
The entire ZIP file is actually two completely different interwoven ZIP files, each hidden within the ignored regions of the other.
Which file you find, `Report.pdf` or `Hacker.pdf`, depends on your high-level parsing strategy, which I'll explain more later.
In order to detect that there was this kind of ambiguity, it would require implementing the parser twice,
doubling the maintenance effort and slowing down the runtime performance dramatically.
It could possibly be done more simply than this with clever optimizations, but most implementers aren't going to think of those.

Attempting to require all ZIP implementations guard against this kind of subtle attack simply won't work.
Some software engineers will inevitably chose to write a "simple" implementation that disregards all the advanced and difficult stuff.
Security measures that are too hard to implement aren't going to be implemented consistently,
and inconsistent security measures are security vulnerabilities.

My proposed solution to this difficult situation is to denounce any implementation that uses the wrong parsing strategy as wholly incorrect.
We don't need everyone to implement two strategies; we just need everyone to use the one true strategy, and there will be no confusion.
If any implementation looks at that ZIP file I linked above and sees `Report.pdf`, it is wrong.
The Gmail attachment preview is wrong, and Google should fix it (it's on my list of bug reports to file; I will update this blog post with further information.).

For every security problem in the ZIP file format, I'm making one of two recommendations:

1. If the problem is easy to detect, everyone should detect it.
2. If the problem is hard to detect, everyone should use one canonical interpretation of the information so that there's no miscommunication between implementations, and then there is no problem to detect.

That second recommendation isn't always easy to follow.
Sometimes it requires throwing away _all_ your code and starting again from scratch, as is the case with 4 implementations I've been researching.
It's not reasonable to ask people to throw away all their code, so an intermediate mitigation is to document known security issues.
Those 4 implementations should warn users in their docs that the code is fundamentally wrong, and one of them already does this!
If we can't afford to repair a treacherous bridge, at least we need a warning sign in front of it.

### Security vs Compatibility

Another compelling reason to disregard the advice of security researchers is that guarding against _potentially_ malicious ZIP files might falsely reject harmless ZIP files created by implementations that made honest mistakes.

One honest mistake that is well documented is Microsoft's `System.IO.Compression.ZipFile` class in .NET versions 4.5.0 until 4.6.1,
which accidentally produced ZIP files with backslashes in file names.
APPNOTE has always declared backslashes illegal in file names; even on Windows, ZIP files must use forward slashes to delimit directory components.
However, Microsoft's bug resulted in corrupted ZIP files spreading around the internet and being archived forever.
Now that we're in this situation what do we do?

APPNOTE's guidance is to reject all of these ZIP files as corrupted, but two different real life human beings reported bugs against my ZIP reader implementation to please support these corrupted ZIP files anyway ( https://github.com/thejoshwolfe/yauzl/issues/66 https://github.com/thejoshwolfe/yauzl/issues/88 ).

So what is the "correct" interpretation of the ZIP file format?
What SHOULD we do, and does that deviate from what's "correct" to do?
I hope not.

My solution is to update the officially correct interpretation of a ZIP file to accept backslashes as equivalent to forward slashes.
Everyone must now workaround the bug the Microsoft introduced to the ZIP world.
It's not difficult or problematic to simply canonicalize slash direction when reading a ZIP file;
you just have to be told to do it.

I don't think every possible problem should be worked around like this.
This particular bug is well-documented in a high-profile implementation, and we've got lots of data points floating around the internet that advocate for this workaround.
If other problems don't have this kind of evidence, we shouldn't work around them.

A well known example of an attack vector in ZIP files (and any other archive format) is path traversal attacks.
A ZIP file might say that a file is named `Report.pdf` or `Archive/2015/Report.pdf`, and those are fine.
But what if the file is named `C:/Windows/System32/malware.dll`?
Absolute paths like that are always an attack, as far as I can tell, but some ZIP implementations workaround it like it's an honest mistake.

Most of my testing is on Linux, and an example of a malicious path on Linux is `/etc/passwd`.
Rust's `zip` crate quietly skips over these malicious entries,
Python's standard library `extractall()` reinterprets the path as `etc/passwd`,
and many other implementations including Go's and Java's standard libraries faithfully report the file name as-is and expect someone else to handle the problem.

Only 4 implementations (out of a little more than a dozen I tested) report an error for `/etc/passwd`, and only 1 implementation reports an error for `C:/Windows/System/malware.dll` when running on Linux.
All implementations should either report an error for these (regardless of which operating system they're running on),
or should document a warning that explicitly passes on responsibility.

It's possible that working around path traversal attacks is justified by some honest mistake that happened in the past, like the Microsoft bug.
Did such an honest mistake happen? I actually don't know. I haven't seen evidence of it.
I believe that implementations should loudly report an error if ever presented with a path traversal attack rather than quietly working around it, and that's what Common ZIP says today, but I might be wrong.
If anyone has information on why this should be updated, please let me know (links in the References at the end).

### Some incorrect behavior is no big deal

The goal for the Common ZIP spec is to eliminate all ambiguity and to clearly delineate correct from incorrect behavior.
However, some incorrect behavior just doesn't matter that much and isn't worth reporting bugs over.

ZIP files contain metadata about files in addition to just their name.
The "last modified" timestamp of each file must always be encoded in a ZIP file at least once,
but there are 2 more ways to encode this information as well.
If an implementation gets the timestamp wrong when reading a ZIP file, that's not security critical.
Common ZIP specifies how to interpret the 3 different encodings, but ZIP readers are free to just ignore this and do it however they want.

The Common ZIP test suite categorizes behavior 3 ways:

1. Pass; the behavior is conformant to the spec.
2. Tolerable; the behavior is incorrect, but it's unlikely to cause any security issue, so no big deal.
3. Danger; the behavior is incorrect, and could plausibly lead to a security problem.

While it would be very nice to achieve a Pass score for every test case, it's really not necessary.
The important result is whether the behavior gets a Danger score or not.
The action I expect maintainers to take is to either fix the dangerous behavior or at least warn about it in the software's documentation.

### Inefficient debates

This is not related to security, but it's an important motivation for making a new spec.
When the authoritative source of information is unclear, then people spend their enthusiasm arguing with each other instead of making cool software.

Mark Adler is a big name in software engineering; he's no dummy.
After publishing a ZIP implementation that demonstrates a novel approach to reading ZIP files (link in the References),
he spent his time arguing with people who posted bug reports accusing his code of not being compliant with the spec.
Who is right? Is Mark Adler's read of a technical specification accurate, or @greggman on GitHub?
(@greggman is the author of another ZIP implementation and is also very knowledgeable.)

APPNOTE is ambiguous, so the truth is they're both right!
Think of all the cool software Mark Adler and everyone else participating in these kinds of discussions could be making instead of arguing over the interpretation of a technical specification.
Think of the cool software _you_ could be making instead of reading any of this blog post!
We're here because APPNOTE's ambiguity is draining humanity's collective enthusiasm, and I want to save us from this time sink.

A world where the "correct" interpretation of the ZIP file spec is a combination of an old confusing document,
nuanced knowledge of existing implementations, and bespoke bug reports from independent security researchers is a world where innovating is unnecessarily expensive.

And the distributed nature of independent security researchers is a waste of their time too.
I recently received a private email reporting security bugs in my ZIP implementation,
and while I appreciate volunteer effort to improve each other's software, this particular report was not very helpful.
Imagine if instead of N researchers emailing M ZIP implementers, we could have a central discussion forum for these issues and reach consensus.
That is what the GitHub issues forum provides in the Common ZIP spec repo.

There will still be time spent arguing over the true meaning of the ZIP file format in the GitHub issues, and that's a good thing.
Come join the discussion!
It should be happening in a centralized forum about the ZIP file format itself, not attached to every individual ZIP implementation separately starting from scratch every time.
Evidence should be presented, a ruling should be made, and then a central authority will serve as a reference for everyone to compare to.

And it's fine if implementations want to deviate from the Common ZIP spec, but now it will be possible to precisely communicate what the deviation is.
With APPNOTE, documenting how you deviate from it is so difficult due to APPNOTE's ambiguities that you must effectively rewrite large chunks of the technical spec anyway on the way to explaining how your software works.
(Examples I will explain later are: Data Descriptors, EOCDR Signature Search, File Name Charset, Zip64 Format Detection, and more.)
In almost all circumstances I encountered in my research, implementations don't document their deviation from the spec at all,
and it's up to @greggman and others to start impassioned discussions here and there all over the internet to get to the bottom of it.

Let's bring our enthusiasm for technical precision to a productive, structured environment where we can all listen to each other and be heard (link in the References).
I'll go first, and I've written a complete technical spec as a starting point for the discussion.

## The ZIP Utopia

Before I go on, I want to thank you for reading this far.
If you know anyone who deals with low-level ZIP file software, please share this post with them.
All the work that I've done is useless if nobody cares, and so thank you for caring enough to get this far.

If you'd like to discuss this blog post specifically, you can do that here: https://github.com/thejoshwolfe/wolfesoftware.com/pull/2 (requires a GitHub account).

We're about to dive into the technical details, because I want to be specific about the very real problems and real solutions we're dealing with.
Unfortunately, there is no way to do that without breaking out the binary layout diagrams and using phrases like "32-bit unsigned integer".
If you're not interested in that kind of thing, it's ok to stop here, and thanks again for reading. 🙂

Alright, let's get into it.

### The structure of a ZIP file

At the time of writing this blog post, I've chosen to impose a no-images limitation on myself for reasons you can read about in the markdown-looks-good project (link in the References),
so for now you get plain-text art.

Here's a rough diagram of an example ZIP file containing an MP3 file:

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

Here are some observations that you might not guess if you were inventing your own archive format from first principles:

* Each `entry.fileName` is in there twice, once right before the corresponding `entry.contents` in the `LocalFileHeader` and once in a centralized listing of just the metadata called the Central Directory. The `entry.contents` bits comprise the vast majority of a typical ZIP file, which means the `LocalFileHeader` structs are scattered throughout, often several megabytes apart. The Central Directory is relatively small, often only a few kilobytes total. So if all you want is a preview of the file names without extracting them all, the Central Directory provides a very efficient place to start.
* The Central Directory is at the end of the ZIP file, not the beginning. This generally makes writing ZIP files slightly easier, and reading them slightly harder.
* The `entry.st_mode` field is only in the `CentralDirectoryHeader`, not the `LocalFileHeader`.
* If you're writing a ZIP file, you need to know the `entry.fileSize` before you write the compressed `entry.contents`, which often means compressing the contents into a tempfile to measure the size, then concatenating it to the final `.zip` file. (There's more nuance to this that I'll get into later.)
* If you're reading a ZIP file, you can either stream it from the beginning reading metadata from each `LocalFileHeader`, or you can start at the end with the Central Directory and follow the pointers to extract individual entries as needed. (These are the two parsing strategies I alluded to earlier; end-first is the one true strategy, and I denounce the beginning-first strategy as simply incorrect. More on that later.)

(I'm still glossing over lots of details here.
I'll add more details as we go in this blog post, but if you're anxious to get the full story,
feel free to read the Common ZIP spec linked in the References at the end.)

#### EOCDR Signature Search

Let's walk through the strategy of starting at the end and reading the Central Directory.
To find the first `CentralDirectoryHeader`, you read the `centralDirOffset32` field from the `EndOfCentralDirectoryRecord`, which has this structure:

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

The `centralDirOffset32` field is at offset 16 out of 22 in the struct, and the struct is right at the end of the file.
Does that mean we just need to read offset `end - 6` to find our field?

Yes, usually. But sometimes no.

The last field of the `EndOfCentralDirectoryRecord` struct is a variable-sized comment of arbitrary bytes.
Its length is encoded in the `archiveCommentLength` field, which is _before_ the `archiveComment` itself.

This is a critical design flaw in the ZIP file format, and it's been there since version 1.0 in 1989 (I checked).
The first thing you need to do in a ZIP file is read the `EndOfCentralDirectoryRecord`, but you don't know where it is until you read the `EndOfCentralDirectoryRecord`.
APPNOTE gives you guidance on how this is supposed to be resolved, but reading between the lines suggests that perhaps the intent is to scan the data until you find the `signature` value `0x06054b50`.

But how do you scan? Do you start at the last possible position `end - 22` and scan backwards? Or do you start at the earliest possible position `end - 65557` and scan forwards?
Do you bother checking the last `21` bytes of the file for the signature even though an `EndOfCentralDirectoryRecord` wouldn't fit that far forward?
Do you bother checking before `end - 65557` even though a max-length comment wouldn't fill the rest of the file?

I tested existing implementations to see what they do, the behavior is all over the map.

#### Data Descriptors

TODO

#### File Name Charset

TODO

#### Zip64 Format Detection

TODO

## Why not update APPNOTE?

The official process for updating APPNOTE is to send snail mail or email to PKWARE and wait for a reply.
I did this on 2025-February-1st suggesting a few example changes and asking if they would be interested in discussing it further.
(Full text of my email is here: https://wolfesoftware.com/email-to-pkware.html .)
6 months later, I haven't gotten any response.

Other examples are TODO: talk about that wikipedia thing, and how they allegedly clarified junk data cannot follow the eocdr comment, but then they still didn't update APPNOTE to say that.

Conclusion: the process for contributing to PKWARE's APPNOTE is too lethargic.
We need a modern open-source model that facilitates open discussions.

## References

* Common ZIP website: https://commonzip.org/
* Common ZIP spec: https://commonzip.org/spec/
* Common ZIP tests: https://commonzip.org/test/
* **APPNOTE**: The official technical specification of the ZIP file format from PKWARE, Inc. https://support.pkware.com/pkzip/appnote (version 6.3.10, as of writing this).
* **yazl**: My JavaScript implementation to create ZIP files: https://github.com/thejoshwolfe/yazl
* **yauzl**: My JavaScript implementation to read ZIP files: https://github.com/thejoshwolfe/yauzl
* **markdown-looks-good**: The renderer for this blog post which doesn't support images: https://github.com/thejoshwolfe/markdown-looks-good
* Gynvael Coldwind's in-depth talk on ZIP vulnerabilities: https://gynvael.coldwind.pl/?id=682
* Mark Adler and @greggman discussing the ambiguities in APPNOTE, including @greggman's report of PKWARE's responses to requests for clarification: https://github.com/madler/sunzip/issues/7
* discuss this blog post here: https://github.com/thejoshwolfe/wolfesoftware.com/pull/2 (requires a GitHub account).
