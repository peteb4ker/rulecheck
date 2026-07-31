import SwiftUI

/// Renders an authored rule as structure — state rows, branches, truth
/// tables, steps, penalty tiers, terms — rather than as a paragraph of
/// prose. This is the payoff of the structured rulebase: the shape of the
/// rule is visible at a glance instead of buried in a sentence.
struct StructuredRuleView: View {
    let structure: RuleStructure

    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            if let summary = structure.summary {
                Text(summary)
                    .font(.title3)
                    .foregroundStyle(Palette.ink)
                    .fixedSize(horizontal: false, vertical: true)
            }

            switch structure.archetype {
            case .mechanic: mechanic
            case .procedure: procedure
            case .penalty: penalty
            case .definition: definition
            case .note: note
            }
        }
    }

    // MARK: mechanic — what is true, what happens next, what it blocks

    @ViewBuilder private var mechanic: some View {
        if let state = structure.state, !state.isEmpty {
            block("WHILE IN EFFECT") {
                ForEach(Array(state.enumerated()), id: \.offset) { index, fact in
                    Label { Text(fact).foregroundStyle(Palette.body) } icon: {
                        if let glyph = structure.stateGlyphs?.at(index) {
                            GlyphView(glyph: glyph).padding(.top, 2)
                        } else {
                            Circle().fill(Palette.accent).frame(width: 5, height: 5)
                                .padding(.top, 7)
                        }
                    }
                    .labelStyle(.titleAndIcon)
                    .fixedSize(horizontal: false, vertical: true)
                }
            }
        }

        if let branch = structure.branch {
            block(branch.when.uppercased()) {
                VStack(spacing: 8) {
                    ForEach(Array(branch.options.enumerated()), id: \.offset) { index, option in
                        HStack(alignment: .top, spacing: 12) {
                            branchCondition(option: option,
                                            glyph: structure.branchGlyphs?.at(index))
                                .frame(width: 96, alignment: .leading)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(option.outcome)
                                    .font(.subheadline.weight(.semibold))
                                    .foregroundStyle(Palette.ink)
                                if let detail = option.detail {
                                    Text(detail).font(.caption).foregroundStyle(Palette.secondary)
                                }
                            }
                            Spacer(minLength: 0)
                        }
                        .padding(12)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Palette.surface, in: RoundedRectangle(cornerRadius: 10))
                    }
                }
            }
        }

        if !structure.orderedEffects.isEmpty {
            block("EFFECTS") {
                VStack(spacing: 0) {
                    ForEach(Array(structure.orderedEffects.enumerated()), id: \.offset) { index, effect in
                        HStack(spacing: 8) {
                            if let glyph = structure.effectGlyphs?.at(index) {
                                GlyphView(glyph: glyph)
                            }
                            Text(effect.label).font(.subheadline).foregroundStyle(Palette.body)
                            Spacer()
                            Text(effect.value)
                                .font(.subheadline.weight(.medium))
                                .foregroundStyle(Palette.ink)
                        }
                        .padding(.vertical, 9)
                        if index < structure.orderedEffects.count - 1 {
                            Divider().overlay(Palette.hairline)
                        }
                    }
                }
                .padding(.horizontal, 12)
                .background(Palette.surface, in: RoundedRectangle(cornerRadius: 10))
            }
        }

        if let ends = structure.endsWhen, !ends.isEmpty {
            block("ALSO ENDS IF") {
                ForEach(ends, id: \.self) { item in
                    Text(item).font(.subheadline).foregroundStyle(Palette.body)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    /// A branch condition and its glyph.
    ///
    /// A chip whose text is the condition would print the same word twice, so
    /// it replaces the text instead of sitting beside it. That is how HEADS
    /// and TAILS read: the chip is the word. Anything else shows both, since
    /// the glyph is then saying something the text does not.
    @ViewBuilder
    private func branchCondition(option: RuleStructure.BranchOption,
                                 glyph: GlyphMark?) -> some View {
        if let glyph, let chip = glyph.chip,
           chip.caseInsensitiveCompare(option.condition) == .orderedSame {
            GlyphView(glyph: glyph)
        } else {
            HStack(spacing: 6) {
                if let glyph { GlyphView(glyph: glyph) }
                Text(option.condition)
                    .citationStyle()
                    .foregroundStyle(Palette.accent)
            }
        }
    }

    // MARK: procedure — ordered steps

    @ViewBuilder private var procedure: some View {
        if let steps = structure.steps, !steps.isEmpty {
            block("STEPS") {
                VStack(alignment: .leading, spacing: 10) {
                    ForEach(Array(steps.enumerated()), id: \.offset) { index, step in
                        HStack(alignment: .top, spacing: 12) {
                            Text("\(index + 1)")
                                .citationStyle()
                                .foregroundStyle(Palette.accent)
                                .frame(width: 20, alignment: .trailing)
                            VStack(alignment: .leading, spacing: 3) {
                                if let actor = step.actor {
                                    Text(actor.uppercased()).sectionLabelStyle()
                                }
                                Text(step.action).font(.subheadline).foregroundStyle(Palette.ink)
                                    .fixedSize(horizontal: false, vertical: true)
                                if let note = step.note {
                                    Text(note).font(.caption).foregroundStyle(Palette.secondary)
                                        .fixedSize(horizontal: false, vertical: true)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // MARK: penalty — infraction, tiers, handling

    @ViewBuilder private var penalty: some View {
        if let infraction = structure.infraction {
            block("INFRACTION") {
                Text(infraction).font(.subheadline).foregroundStyle(Palette.ink)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }

        if let rows = structure.basePenalty, !rows.isEmpty {
            block("PENALTY") {
                VStack(spacing: 8) {
                    ForEach(rows) { row in
                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Text(row.tier.uppercased()).sectionLabelStyle()
                                Spacer()
                                Text(row.penalty)
                                    .font(.subheadline.weight(.semibold))
                                    .foregroundStyle(Palette.negative)
                            }
                            if let note = row.note {
                                Text(note).font(.caption).foregroundStyle(Palette.secondary)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                            if let examples = row.examples, !examples.isEmpty {
                                ForEach(examples, id: \.self) { example in
                                    Text("· \(example)")
                                        .font(.caption).foregroundStyle(Palette.body)
                                        .fixedSize(horizontal: false, vertical: true)
                                }
                            }
                        }
                        .padding(12)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Palette.surface, in: RoundedRectangle(cornerRadius: 10))
                    }
                }
            }
        }

        if let handling = structure.handling, !handling.isEmpty {
            block("HANDLING") {
                ForEach(handling, id: \.self) { item in
                    Text("· \(item)").font(.subheadline).foregroundStyle(Palette.body)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }

        if let upgrades = structure.upgradeConditions, !upgrades.isEmpty {
            block("UPGRADES") {
                ForEach(upgrades, id: \.self) { item in
                    Text(item).font(.subheadline).foregroundStyle(Palette.body)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    // MARK: definition — term list

    @ViewBuilder private var definition: some View {
        if let terms = structure.terms, !terms.isEmpty {
            VStack(alignment: .leading, spacing: 0) {
                ForEach(Array(terms.enumerated()), id: \.offset) { index, term in
                    VStack(alignment: .leading, spacing: 3) {
                        Text(term.term).font(.subheadline.weight(.semibold))
                            .foregroundStyle(Palette.ink)
                        Text(term.meaning).font(.subheadline).foregroundStyle(Palette.body)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .padding(.vertical, 10)
                    if index < terms.count - 1 { Divider().overlay(Palette.hairline) }
                }
            }
        }
    }

    // MARK: note — paragraphs

    @ViewBuilder private var note: some View {
        if let paragraphs = structure.paragraphs, !paragraphs.isEmpty {
            VStack(alignment: .leading, spacing: 12) {
                ForEach(paragraphs, id: \.self) { paragraph in
                    Text(paragraph).font(.body).foregroundStyle(Palette.body)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    // MARK: shared

    @ViewBuilder
    private func block<Content: View>(_ label: String,
                                      @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(label).sectionLabelStyle()
            content()
        }
    }
}
