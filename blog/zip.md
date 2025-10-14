# I Fixed The ZIP File Format

The `.zip` file format is a general-purpose archive format implemented by dozens (possibly hundreds) of different software programs that use the format to communicate with each other.
The official technical specification, called APPNOTE, is maintained by the for-profit corporation PKWARE, Inc. who originally created the format.
(Link in the References section.)
It's critical that these different implementations agree on what the ZIP file format is so that there aren't any accidental or intentional miscommunications.

The ZIP file format has a lot of problems, which I first encountered writing my own implementation in JavaScript (links to yazl and yauzl in the References section).
These problems include ambiguities in the structure, missing specification for important details,
and generally being a very old document (originally from 1989, last updated in 2022) in sore need of major updates.

For 10 years I worked around the problems, conducted my own research on how different implementations behaved,
fielded bug reports from security researchers, and advocated a sensible interpretation of APPNOTE to other authors of ZIP implementations.
After enough evidence piled up that the real problem was in APPNOTE itself, I reached out to PKWARE to offer improvements.
From both the lack of response to my inquiry and the stories I found of PKWARE's handling of others' inquiries,
I lost hope that PKWARE was going to address the problems and make the updates that APPNOTE needed.

This blog post is an announcement of a project I've been working on for much of the year 2025 to create a complete re-specification of the ZIP file format from scratch independent of APPNOTE.
Common ZIP is an open-source project by the people for the people, and it's here to solve all of ZIP's problems.

Disclaimers:

* I do not want your money. This is a volunteer effort that I'm very proud to share with the world.
* This blog post is most relevant to maintainers of ZIP software and of systems that use ZIP files in an automated fashion. End users who interact with ZIP files by clicking with a mouse are generally not affected by anything here.
* There is a discussion of security issues in the ZIP file format, but as noted above these are actionable by maintainers of software and software systems, not by end users. If you're not technical, you don't have anything to worry about.
* I am not inventing a new format. This project advocates for minor changes to existing ZIP implementations to get everyone on the same page about what the ZIP file format really is, and almost all existing ZIP files will continue to work.
* While most of the changes I'm advocating are minor, the one major exception is that streaming readers of ZIP files should all be deprecated, a major disruption to niche ZIP use cases. This is explained below.

So what are ZIP's problems and how did I solve them?

## Ambiguities

The ZIP file format includes several redundant values, and APPNOTE almost never specifies how conflicts in these redundant values should be handled.

Consider this example taken from the `EndOfCentralDirectoryRecord`.
The struct includes the following fields:

* `centralDirOffset32` - the byte offset where an array of items starts
* `centralDirSize32` - the size in bytes of the array
* `entryCount16` - the number of items in the array

This is overspecified.
Given the offset and count you can derive the size, or given the offset and size you can derive the count.
(It's a bit more complex than pointer arithmetic due to each `CentralDirectoryHeader` being variable sized, but still straightforward to derive.
And there's even a hidden 4th redundant value, the byte offset where the array ends.)

So what is a ZIP reader supposed to do when a ZIP file claims there is only 1 `CentralDirectoryHeader` in the array while the byte range actually includes 2 coherent `CentralDirectoryHeader` structs?

1. Trust the count and stop after 1?
2. Or trust the byte range and include both?

The correct behavior is option 3: produce an error because the ZIP file is most likely malicious.

But do existing implementations produce an error?
Part of the Common ZIP project is an expansive test suite to study the behavior of existing implementations.
Among the dozen or so implementations I tested, only 1 reports an error consistently for this category of disagreement.
Almost all implementations are about 50/50 on picking the size or the count with no warning, including my implementation yauzl.
(The one implementation that gets this right is command line `unzip` from Info-ZIP.
This is the `entryCount16 1/2` and related tests. Link to the table in References.)

APPNOTE simply states that the values are correct, for example:
`4.4.23 size of the central directory: (4 bytes) The size (in bytes) of the entire central directory.`.
No acknowledgement of redundancy, no precedence for one interpretation over another, no caution against potentially malicious inputs.
(While APPNOTE sometimes uses ISO verbs like `MUST` and `SHOULD` in all-caps, there is no ISO verb used for these field definitions.)
When simply stated like this, the implication is that an implementation can trust that the value is correct.

## File Types

TODO

## Technical Language

APPNOTE uses the all-caps verb forms MUST, SHALL, SHOULD, and MAY (and MUST NOT, SHOULD NOT, etc.).
Section `3.0 Notations` defines what these terms mean, and they deviate subtly from the ISO standard that most technical writing uses.
In particular, APPNOTE defines `3.5 MAY indicates an OPTIONAL element.`, where ISO defines MAY to mean "is permitted".
I have come to understand that when APPNOTE says OPTIONAL here, they mean that the element's presence is conditional, not that its presence is implementation defined.

This confusion has led to real bugs.
`4.3.5 File data MAY be followed by a "data descriptor" for the file.`
I interpreted this MAY to mean that it was up to me to include the "data descriptor" or not,
but really its presence is conditional on general purpose bit 3 (which is specified clearly elsewhere in 4.3.9.1).
@joaomoreno on GitHub reported the bug where the ZIP files created by my implementation couldn't be read by Apple's implementation
https://github.com/thejoshwolfe/yazl/issues/14 .
This problem stemmed from me misunderstanding APPNOTE's use of "MAY".

Some minor complaints that could easily be cleaned up are the use of "MAY NOT", which is never defined, in 3 places.
It's not confusing in context, but also it has nothing to do with conditionally included elements, which is the definition of MAY used above.
The phrase should really just be written in lowercase "may not" avoiding the formally defined forms, and it would fix the issue.

Additionally, APPNOTE seems to believe that 0-size elements do not exist, which is an interesting philosophical stance that I find unnecessarily convoluted.
Some examples:
* `If input came from standard input, there is no file name field.` (4.4.17) rather than "the file name has 0 size", which is what 4.4.12 says. (Also standard input is not a concept in the ZIP file format; it's a behavioral detail of some implementation, probably PKZIP, so it doesn't belong in this specification; and entries with empty file names are a bad idea for security reasons that many implementations wisely do not support.)
* `Zero-byte files, directories, and other file types that contain no content MUST NOT include file data.` (4.3.8) rather than saying something like "file data MAY have 0 size and MUST have 0 size for directories". (Also see the File Types section in this blog post for criticism of how APPNOTE fails to specify how to encode directories and other file types.)

Saying "zero-byte files MUST NOT include file data" is pretty silly,
like saying "1 + 1 MUST equal 2".
But the real confusing part is suggesting that the file name field is deleted under some circumstances instead of just having 0 size.

Putting together philosophical confusion and simply incorrect use of their own verb forms, here's another example:
`Immediately following the local header for a file SHOULD be placed the compressed or stored data for the file.` (4.3.8).
APPNOTE defines "SHOULD" as `a RECOMMENDED element`, so is this a recommendation to put the data in the only place where it's allowed to go?
Where else would it go? What else would I do other than follow this recommendation?
I think the real intent is to say that files "SHOULD NOT" have 0 size, for some reason, and then because having >0 size is the only way for something to exist according to APPNOTE, that's where this idea comes from that the file data "SHOULD" be after the local header.
Or maybe I'm totally wrong about this; although I've been studying this document for like a hundred hours, I still have low confidence I understand what the authors are trying to communicate.
If you've got a better explanation, let me know (link in the References for discussing this blog post).

So what's the solution? Just be consistent with technical writing style.

The writing style in Common ZIP is to use "SHALL" to delineate correct from incorrect.
Take the `crc32` field for example.
Common ZIP specifies "The `crc32` SHALL be the CRC32 of the corresponding `contents`.". ( https://commonzip.org/spec/#Central-Directory )
Contrast this with APPNOTE, which never explicitly defines what this field even means,
and uses the phrases "this field is set to" and "the correct value is put in" (4.4.7).
In this `crc32` case, there is a correct value and an incorrect value, so Common ZIP uses "SHALL".

Common ZIP uses "SHOULD" to explicitly indicate that there are multiple permissible options, but there's a good reason to choose one of them.
Continuing the `crc32` example,
Common ZIP advises "A reader SHOULD require that the CRC32 of the `contents` is equal to `crc32`. If it is not, this typically indicates unintentional single-bit data corruption.". ( https://commonzip.org/spec/#Jumping-to-LocalFileHeader-and-fileData )
This allows readers who are unconcerned with detecting corruption to compliantly ignore the `crc32` field,
and gives rationale for why it is recommended that most readers verify it.

Common ZIP uses "MAY" to explicitly permit something that would be forbidden if not called out.
For example, "As a special case, `dosTimestamp` MAY be `0`, which means that `dosTimestamp` field has no meaning.". ( https://commonzip.org/spec/#lastModifiedTimestamp )
Common ZIP does not use "MAY NOT", because it is ambiguous in common English.

Common ZIP uses "CAN" to bring attention to corner cases and possibilities that might be counterintuitive.
For example, "If the `signature` field is present, it SHALL be `0x08074b50`. Note that the `crc32` field CAN have this value by coincidence.". ( https://commonzip.org/spec/#DataDescriptor )

Common ZIP does not use any all-caps verb form for definitions.
In contrast to SHALL which is always used for situations where something is disallowed, definitions give meaning to whatever is there.
For example, "Before the first `CentralDirectoryHeader` is optional unused space. Then, for each entry, there is a `CentralDirectoryHeader`.". ( https://commonzip.org/spec/#Central-Directory )
This defines a region of bytes as a `CentralDirectoryHeader`, and then places restrictions on the bytes therein with statements like "The `signature` SHALL be `0x02014b50` i.e. `{0x50, 0x4b, 0x01, 0x02}`.".

Getting the technical language right matters.
I've probably made mistakes in my document so far, but I have a pretty clear policy that I'm following for technical writing style
that I believe solves real problems.

## References

* Common ZIP website: https://commonzip.org/
* Common ZIP spec: https://commonzip.org/spec/
* Common ZIP tests: https://commonzip.org/test/
* **APPNOTE**: The official technical specification of the ZIP file format from PKWARE, Inc. https://support.pkware.com/pkzip/appnote (version 6.3.10, as of writing this).
* **yazl**: My JavaScript implementation to create ZIP files: https://github.com/thejoshwolfe/yazl
* **yauzl**: My JavaScript implementation to read ZIP files: https://github.com/thejoshwolfe/yauzl
* discuss this blog post here: https://github.com/thejoshwolfe/wolfesoftware.com/pull/2 (requires a GitHub account).
