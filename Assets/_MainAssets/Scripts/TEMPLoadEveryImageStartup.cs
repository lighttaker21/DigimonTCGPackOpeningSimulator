using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using System.IO;
using System.Threading.Tasks;
using TMPro;
using UnityEngine.SceneManagement;

// NOTE: this script's local-file lookup (ImageGetData.GetCardImageFromFile,
// which checks Application.dataPath + "/Images/{id}.jpg|png") is preserved
// as-is. It is now extended with a fallback to CardImageLoader, which
// downloads/caches the same art from digimon-card-app at runtime when no
// local file is present. See CardImageLoader.cs for the full pipeline
// explanation (source URL, disk cache path, WebP-decoding caveat).
public class TEMPLoadEveryImageStartup : MonoBehaviour
{
    //public List<Sprite> CardImages = new List<Sprite>();
    public CardSet EveryCard;
    public CardVariable defaultCard;
    //public TextMeshProUGUI loadingPercent;
    public Slider loadingPercent;
    public float totalCards;
    public string sceneToLoad;
    private async void Awake()
    {
        DontDestroyOnLoad(gameObject);
        totalCards = EveryCard.ListOfCardsInSet.Count;
        SceneManager.LoadScene(sceneToLoad);
        for (int i = 0; i < EveryCard.ListOfCardsInSet.Count; i++)
        {
            CardVariable card = EveryCard.ListOfCardsInSet[i];
            card.cardImage = await ImageGetData.GetCardImageFromFile(card.name);
            if (card.cardImage == null)
            {
                await CardImageLoader.LoadAndAssignAsync(card);
            }
            loadingPercent.value = (((i + 1) / totalCards) * 100);
        }
        defaultCard.cardImage = await ImageGetData.GetCardImageFromFile(defaultCard.name);
        if (defaultCard.cardImage == null)
        {
            await CardImageLoader.LoadAndAssignAsync(defaultCard);
        }
        Destroy(gameObject);
    }
}
