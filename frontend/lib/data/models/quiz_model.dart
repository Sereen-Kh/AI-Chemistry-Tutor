class QuizOption {
  final String letter;
  final String name;
  final String detail;

  const QuizOption({
    required this.letter,
    required this.name,
    required this.detail,
  });
}

class QuizQuestion {
  final int number;
  final int total;
  final String question;
  final String hint;
  final String hintSymbol;
  final List<QuizOption> options;
  final String correctLetter;
  final String configLabel;

  const QuizQuestion({
    required this.number,
    required this.total,
    required this.question,
    required this.hint,
    required this.hintSymbol,
    required this.options,
    required this.correctLetter,
    required this.configLabel,
  });

  static List<QuizQuestion> get defaults => const [
        QuizQuestion(
          number: 4,
          total: 10,
          question: 'Which element has the atomic number 1?',
          hint: 'Lightest and most abundant element in the universe.',
          hintSymbol: 'H',
          options: [
            QuizOption(letter: 'A', name: 'Helium', detail: 'Atomic Mass: 4.0026'),
            QuizOption(letter: 'B', name: 'Hydrogen', detail: 'Atomic Mass: 1.0078'),
            QuizOption(letter: 'C', name: 'Lithium', detail: 'Atomic Mass: 6.941'),
            QuizOption(letter: 'D', name: 'Beryllium', detail: 'Atomic Mass: 9.0122'),
          ],
          correctLetter: 'B',
          configLabel: '1s¹ Configuration',
        ),
        QuizQuestion(
          number: 5,
          total: 10,
          question: 'What is the chemical symbol for Gold?',
          hint: 'This element has been prized throughout human history.',
          hintSymbol: 'Au',
          options: [
            QuizOption(letter: 'A', name: 'Go', detail: 'Atomic Mass: N/A'),
            QuizOption(letter: 'B', name: 'Gd', detail: 'Atomic Mass: 157.25'),
            QuizOption(letter: 'C', name: 'Au', detail: 'Atomic Mass: 196.97'),
            QuizOption(letter: 'D', name: 'Ag', detail: 'Atomic Mass: 107.87'),
          ],
          correctLetter: 'C',
          configLabel: '[Xe] 4f¹⁴ 5d¹⁰ 6s¹',
        ),
        QuizQuestion(
          number: 6,
          total: 10,
          question: 'Which bond involves the sharing of two electron pairs?',
          hint: 'Think about the bond order in O₂.',
          hintSymbol: 'O₂',
          options: [
            QuizOption(letter: 'A', name: 'Single Bond', detail: '1 shared pair'),
            QuizOption(letter: 'B', name: 'Double Bond', detail: '2 shared pairs'),
            QuizOption(letter: 'C', name: 'Triple Bond', detail: '3 shared pairs'),
            QuizOption(letter: 'D', name: 'Ionic Bond', detail: 'Electron transfer'),
          ],
          correctLetter: 'B',
          configLabel: 'σ + π bond geometry',
        ),
      ];
}
