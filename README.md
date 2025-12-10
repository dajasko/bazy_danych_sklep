Link do Postmana - https://martian-station-9552411.postman.co/workspace/mlqgang's-Workspace~84068984-4874-4e66-8627-aae8bec472ef/collection/49688293-f999026f-ea9f-4c83-b113-563d49ce30bc?action=share&creator=49688293
Backend posiada wszystkie wymienione we wcześniejszym raporcie transakcje oraz ma zintegrowaną walidację, która uniemożliwia wpisanie quantity, availability, mniejszego od 1, czy niecałkowitego.
W walidacji zostało również uwzględnione, że nie może być dwóch użytkowników o tym samym emailu, czy nazwie, oraz te pola przy tworzeniu użytkownika nie mogą być puste.
Przy dodaniu do koszyka sprawdzane jest, czy quantity mieści się w zakresie availability oraz czy product id się zgadza z istniejącym produktem.
Checkout wymaga statusu "pending". Status shipped można ustawić jedynie jeśli poprzedzający status jest "paid", a zamówienia nie można anulować jeśli status jest "shipped".
Dane zamówienie może zostać anulowane tylko przez składającego to zamówienie. Jest to realizowane przy pomocy tokena.
Wszystkie endpointy (oprócz loginu i rejestracji) wymagają tego, by użytkownik był zalogowany.
