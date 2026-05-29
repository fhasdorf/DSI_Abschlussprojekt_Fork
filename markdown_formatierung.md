MARKDOWN FORMATIERUNGSHILFE

st.title("...")              # riesig, nur für Seitentitel
st.header("...")             # groß, fett
st.subheader("...")          # mittel, fett   ← guter Default für Chart-Titel
st.markdown("#### ...")      # etwas kleiner, fett
st.markdown("##### ...")     # noch kleiner
st.markdown("**...**")       # normal groß, nur fett


    st.markdown("> *„Das ist ein klassisches Zitat, das eingerückt dargestellt wird.“*", unsafe_allow_html=True)