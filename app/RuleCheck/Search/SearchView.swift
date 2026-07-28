import SwiftUI

struct SearchView: View {
    @Bindable var model: SearchViewModel
    let repository: RulesRepository
    @AppStorage("searchScope") private var storedScope: String = SearchScope.all.rawValue
    @State private var path: [Route] = []

    var body: some View {
        NavigationStack(path: $path) {
            List {
                if let message = model.errorMessage {
                    ErrorView(message: message)
                        .listRowBackground(Color.clear)
                } else if model.query.trimmingCharacters(in: .whitespaces).isEmpty {
                    Section {
                        ForEach(model.documents.filter { model.scope.docIds?.contains($0.id) ?? true }) { doc in
                            NavigationLink(value: Route.document(doc)) {
                                HStack(spacing: 14) {
                                    RoundedRectangle(cornerRadius: 10)
                                        .fill(doc.hue)
                                        .frame(width: 34, height: 34)
                                    VStack(alignment: .leading, spacing: 3) {
                                        Text(doc.title)
                                            .font(.headline)
                                            .foregroundStyle(Palette.ink)
                                        (Text("\(model.sectionCounts[doc.id] ?? 0) sections · ")
                                            + Text(doc.published).monospaced())
                                            .font(.caption)
                                            .foregroundStyle(Palette.secondary)
                                    }
                                }
                                .padding(.vertical, 2)
                            }
                            .listRowSeparator(.hidden)
                            .listRowInsets(EdgeInsets(top: 4, leading: 36, bottom: 4, trailing: 36))
                            .listRowBackground(
                                RoundedRectangle(cornerRadius: 16)
                                    .fill(Palette.surface)
                                    .shadow(color: Palette.ink.opacity(0.07), radius: 2, x: 0, y: 1)
                                    .padding(.horizontal, 20)
                                    .padding(.vertical, 4)
                            )
                        }
                    } header: {
                        Text("Documents").sectionLabelStyle()
                    }
                } else if model.groups.isEmpty {
                    ContentUnavailableView.search(text: model.query)
                        .listRowBackground(Color.clear)
                } else {
                    ForEach(model.groups, id: \.doc.id) { group in
                        Section {
                            ForEach(group.hits) { hit in
                                NavigationLink(value: Route.section(hit.section.id)) {
                                    VStack(alignment: .leading, spacing: 5) {
                                        Text(citationLine(hit.section))
                                            .citationStyle()
                                            .foregroundStyle(Palette.secondary)
                                            .lineLimit(1)
                                        Text(hit.section.title)
                                            .font(.headline)
                                            .foregroundStyle(Palette.ink)
                                        Text(SnippetHighlighter.attributed(hit.snippet))
                                            .font(.subheadline)
                                            .foregroundStyle(Palette.body)
                                            .lineSpacing(3)
                                            .lineLimit(2)
                                    }
                                    .padding(.vertical, 2)
                                }
                                .listRowSeparator(.hidden)
                                .listRowInsets(EdgeInsets(top: 4, leading: 36, bottom: 4, trailing: 36))
                                .listRowBackground(
                                    RoundedRectangle(cornerRadius: 16)
                                        .fill(Palette.surface)
                                        .shadow(color: Palette.ink.opacity(0.07), radius: 2, x: 0, y: 1)
                                        .padding(.horizontal, 20)
                                        .padding(.vertical, 4)
                                )
                            }
                        } header: {
                            HStack(spacing: 8) {
                                RoundedRectangle(cornerRadius: 3)
                                    .fill(group.doc.hue)
                                    .frame(width: 8, height: 8)
                                Text("\(group.doc.title) · \(group.hits.count)")
                                    .sectionLabelStyle()
                            }
                        }
                    }
                }
            }
            .listStyle(.plain)
            .scrollContentBackground(.hidden)
            .background(Palette.canvas)
            .safeAreaInset(edge: .top) {
                Picker("Scope", selection: $model.scope) {
                    ForEach(SearchScope.allCases, id: \.self) { Text($0.label).tag($0) }
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
                .padding(.vertical, 6)
                .background(Palette.canvas)
                .overlay(alignment: .bottom) { Palette.hairline.frame(height: 1) }
            }
            .searchable(text: $model.query,
                        placement: .navigationBarDrawer(displayMode: .always),
                        prompt: "Search the rules")
            .searchAutofocus()
            .navigationTitle("Rule Check")
            // The large title never draws once the search drawer is pinned
            // (displayMode: .always) — it reserved its row and left it blank.
            // Inline renders, and a search-first app wants the vertical space.
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    NavigationLink { AboutView(documents: model.documents) } label: {
                        Image(systemName: "info.circle")
                    }
                    .accessibilityLabel("About")
                    .accessibilityIdentifier("About")
                }
            }
            .navigationDestination(for: Route.self) { route in
                switch route {
                case .section(let id):
                    SectionView(id: id, repository: repository, path: $path)
                case .document(let doc):
                    DocumentOutlineView(doc: doc, repository: repository)
                }
            }
            .task(id: model.query) {
                try? await Task.sleep(for: .milliseconds(150))
                guard !Task.isCancelled else { return }
                model.refresh()
            }
            .onChange(of: model.scope) { _, newValue in
                storedScope = newValue.rawValue
                model.refresh()
            }
            .onAppear {
                model.scope = SearchScope(rawValue: storedScope) ?? .all
            }
        }
        .tint(Palette.accent)
    }

    /// Locked results anatomy: "§ n · parent" leading line; non-citable
    /// sections show the parent alone.
    private func citationLine(_ section: RuleSection) -> String {
        let parent = section.breadcrumb.components(separatedBy: " › ").last ?? ""
        if let n = section.citableNumber { return "§ \(n) · \(parent)" }
        return parent
    }
}


func sectionRowTitle(_ section: RuleSection) -> String {
    if let n = section.citableNumber { return "\(n)  \(section.title)" }
    return section.title
}
