import SwiftUI

struct DocumentOutlineView: View {
    let doc: DocumentInfo
    let repository: RulesRepository

    var body: some View {
        if let sections = try? repository.sections(inDocument: doc.id) {
            List(sections) { section in
                NavigationLink(value: section.id) {
                    rowTitle(section)
                        .padding(.leading, section.parentId == nil ? 0 : 16)
                }
                .listRowBackground(Color.clear)
                .listRowSeparatorTint(Palette.hairline)
            }
            .listStyle(.plain)
            .scrollContentBackground(.hidden)
            .background(Palette.canvas)
            .navigationTitle(doc.title)
            .navigationBarTitleDisplayMode(.inline)
        } else {
            ErrorView(message: "Could not load \(doc.title)")
        }
    }

    /// Citable numbers render as mono accent citations; titles stay ink.
    private func rowTitle(_ section: RuleSection) -> Text {
        if let n = section.citableNumber {
            return Text(n).font(.subheadline.monospaced()).foregroundColor(Palette.accent)
                + Text("  ")
                + Text(section.title).foregroundColor(Palette.ink)
        }
        return Text(section.title).foregroundColor(Palette.ink)
    }
}
