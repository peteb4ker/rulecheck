import SwiftUI

/// Renders FTS5 snippets whose match ranges are wrapped in private-use
/// sentinels (see the snippet() call in RulesRepository). Sentinels must
/// never reach the screen: stray or unclosed markers degrade to plain text.
enum SnippetHighlighter {
    static let start: Character = "\u{E000}"
    static let end: Character = "\u{E001}"

    static func attributed(_ raw: String) -> AttributedString {
        var out = AttributedString()
        var plain = ""
        var match = ""
        var inMatch = false

        func flushPlain() {
            if !plain.isEmpty { out += AttributedString(plain); plain = "" }
        }

        for ch in raw {
            switch ch {
            case start where !inMatch:
                flushPlain()
                inMatch = true
            case end where inMatch:
                var run = AttributedString(match)
                run.backgroundColor = Palette.highlight
                run.foregroundColor = Palette.highlightInk
                out += run
                match = ""
                inMatch = false
            case start, end:
                continue
            default:
                if inMatch { match.append(ch) } else { plain.append(ch) }
            }
        }
        if inMatch {
            out += AttributedString(match)
        } else {
            flushPlain()
        }
        return out
    }
}
