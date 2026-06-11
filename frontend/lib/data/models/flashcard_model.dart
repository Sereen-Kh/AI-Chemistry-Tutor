class Flashcard {
  final int id;
  final String state;
  final String term;
  final String formula;
  final String definition;
  final String example;

  const Flashcard({
    required this.id,
    required this.state,
    required this.term,
    required this.formula,
    required this.definition,
    required this.example,
  });

  static List<Flashcard> get defaults => const [
        Flashcard(
          id: 42,
          state: 'ALPHA',
          term: "Avogadro's Number",
          formula: 'Nₐ',
          definition:
              '6.022 × 10²³ particles per mole.\nThe number of particles in exactly one mole of any substance.',
          example: '1 mol of H₂O = 6.022 × 10²³ molecules',
        ),
        Flashcard(
          id: 43,
          state: 'ALPHA',
          term: 'Covalent Bond',
          formula: 'e⁻ share',
          definition:
              'A chemical bond formed by the sharing of electron pairs between two non-metal atoms.',
          example: 'H₂: H—H (one shared pair)',
        ),
        Flashcard(
          id: 44,
          state: 'BETA',
          term: 'Ionic Bond',
          formula: 'e⁻ transfer',
          definition:
              'A bond formed by the complete transfer of electrons from a metal to a non-metal.',
          example: 'NaCl: Na⁺ + Cl⁻',
        ),
        Flashcard(
          id: 45,
          state: 'BETA',
          term: 'Molar Mass',
          formula: 'M (g/mol)',
          definition:
              'The mass of one mole of a substance, in grams per mole.',
          example: 'M(H₂O) = 2(1) + 16 = 18 g/mol',
        ),
        Flashcard(
          id: 46,
          state: 'GAMMA',
          term: "Hess's Law",
          formula: 'ΔH_rxn',
          definition:
              'The total enthalpy change of a reaction is independent of the pathway taken.',
          example: 'ΔH = ΔH₁ + ΔH₂ + ΔH₃',
        ),
      ];
}
