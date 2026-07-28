import SwiftUI

struct SectionView: View {
    let id: String
    let repository: RulesRepository
    @Binding var path: [Route]

    var body: some View {
        if let section = try? repository.section(id: id) {
            content(for: section)
        } else {
            ErrorView(message: "Section \(id) not found")
        }
    }

    @ViewBuilder
    private func content(for section: RuleSection) -> some View {
        let refs = (try? repository.crossReferences(from: section.id)) ?? []
        let neighbors = (try? repository.neighbors(of: section)) ?? (prev: nil, next: nil)
        let doc = try? repository.documentInfo(id: section.docId)

        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(section.breadcrumb)
                    .citationStyle()
                    .foregroundStyle(Palette.secondary)
                title(for: section)
                    .font(.largeTitle.bold())
                if let structure = section.structure {
                    StructuredRuleView(structure: structure)
                } else {
                    // Reference text for sections not yet authored.
                    paragraphs(of: section.body)
                }
                if !refs.isEmpty {
                    Divider().overlay(Palette.hairline)
                    Text("See also").sectionLabelStyle()
                    ForEach(refs) { ref in
                        Button(sectionRowTitle(ref)) { path.append(.section(ref.id)) }
                            .font(.subheadline)
                            .tint(Palette.accent)
                            .frame(minHeight: 44 / 2)
                    }
                }
                if let quotes = section.structure?.quotes, !quotes.isEmpty {
                    Divider().overlay(Palette.hairline)
                    Text("Official wording").sectionLabelStyle()
                    ForEach(Array(quotes.enumerated()), id: \.offset) { _, quote in
                        Text(quote)
                            .font(.callout)
                            .italic()
                            .foregroundStyle(Palette.body)
                            .lineSpacing(3)
                            .padding(.leading, 12)
                            .overlay(alignment: .leading) {
                                Palette.accent.frame(width: 2)
                            }
                            .textSelection(.enabled)
                    }
                }
                if let doc {
                    Divider().overlay(Palette.hairline)
                    // The judge's citation: what to look up, and where.
                    Text(Self.citation(for: section, in: doc))
                        .citationStyle()
                        .foregroundStyle(Palette.secondary)
                        .padding(.top, 12)
                        .textSelection(.enabled)
                }
            }
            .padding(18)
        }
        .background(Palette.canvas)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .bottomBar) {
                Button { if let p = neighbors.prev { path[path.count - 1] = .section(p.id) } } label: {
                    Label("Previous", systemImage: "chevron.up")
                }.disabled(neighbors.prev == nil)
                Spacer()
                Button { if let n = neighbors.next { path[path.count - 1] = .section(n.id) } } label: {
                    Label("Next", systemImage: "chevron.down")
                }.disabled(neighbors.next == nil)
            }
        }
        .tint(Palette.accent)
    }

    /// A citation a judge can read aloud or copy: document, version, date,
    /// and the section number when the section has a citable one.
    static func citation(for section: RuleSection, in doc: DocumentInfo) -> String {
        let base = "\(doc.title) — version \(doc.version), \(doc.published)"
        guard let n = section.citableNumber else { return base }
        return "\(base) · § \(n)"
    }

    /// Title with the § number in accent monospaced — the citable part is
    /// visually the citation, the words are the ink.
    private func title(for section: RuleSection) -> Text {
        if let n = section.citableNumber {
            return Text("§ \(n)").font(.title2.monospaced().bold()).foregroundColor(Palette.accent)
                + Text("  ")
                + Text(section.title).foregroundColor(Palette.ink)
        }
        return Text(section.title).foregroundColor(Palette.ink)
    }

    /// Bodies are newline-joined lines from the pipeline; render each line
    /// as a paragraph with breathing room (typography only — no structure
    /// is invented, and content is verbatim-pending-rewrite per #20).
    private func paragraphs(of body: String) -> some View {
        let parts = body.components(separatedBy: "\n").filter {
            !$0.trimmingCharacters(in: .whitespaces).isEmpty
        }
        return VStack(alignment: .leading, spacing: 10) {
            ForEach(Array(parts.enumerated()), id: \.offset) { _, part in
                Text(part)
                    .font(.body)
                    .foregroundStyle(Palette.body)
                    .lineSpacing(3)
            }
        }
        .textSelection(.enabled)
    }
}
