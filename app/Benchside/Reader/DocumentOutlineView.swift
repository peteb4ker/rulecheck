import SwiftUI

struct DocumentOutlineView: View {
    let doc: DocumentInfo
    let repository: RulesRepository

    var body: some View {
        if let sections = try? repository.sections(inDocument: doc.id) {
            List(sections) { section in
                NavigationLink(value: section.id) {
                    Text(sectionRowTitle(section))
                        .padding(.leading, section.parentId == nil ? 0 : 16)
                }
            }
            .listStyle(.plain)
            .navigationTitle(doc.title)
            .navigationBarTitleDisplayMode(.inline)
        } else {
            ErrorView(message: "Could not load \(doc.title)")
        }
    }
}
